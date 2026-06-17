"""Collector (порт 8001) — сбор цен с бирж в Redis Stream ``prices``.

Запускает:
- по одному ``ExchangeCollector`` на каждую активную биржу из ``exchange_configs``
  (символы берутся из ``tracked_pairs``, по умолчанию BTC/USDT) — фазы 3–4;
- ``BatchWriter`` для записи тиков в TimescaleDB — фаза 5.

Health-эндпоинт показывает число WS-соединений, их статусы, связь с Redis и
количество записанных в БД строк.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

from db_writer import BatchWriter
from exchange_factory import create_exchange
from redis_publisher import RedisPublisher
from ws_client import ExchangeCollector
from shared.config import EXCHANGES, settings
from shared.db import close_db_pool, get_db_pool

log = structlog.get_logger()
SERVICE = "collector"
DEFAULT_SYMBOLS = ["BTC/USDT"]

# ── Prometheus ──
_ws_connections_gauge = Gauge("ws_connections_active", "Активные WS-соединения по биржам")
_ws_messages_gauge = Gauge("ws_messages_total", "Всего опубликовано тиков")

# ── Состояние процесса ──
_state: dict = {
    "publisher": None,       # RedisPublisher
    "collectors": [],        # list[ExchangeCollector]
    "writer": None,          # BatchWriter | None
    "started_at": 0.0,
}


async def _load_targets() -> dict[str, list[str]]:
    """Биржи из exchange_configs (is_active) + их символы из tracked_pairs.

    При недоступности БД — fallback на Binance BTC/USDT (минимум для фазы 3).
    """
    try:
        pool = await get_db_pool()
        ex_rows = await pool.fetch(
            "SELECT exchange FROM exchange_configs WHERE is_active = true ORDER BY exchange"
        )
        pair_rows = await pool.fetch(
            "SELECT symbol, exchange FROM tracked_pairs WHERE is_active = true"
        )
    except Exception as err:  # noqa: BLE001
        log.warning("targets_db_unavailable", error=str(err))
        return {"binance": list(DEFAULT_SYMBOLS)}

    symbols_by_ex: dict[str, list[str]] = {}
    for row in pair_rows:
        symbols_by_ex.setdefault(row["exchange"], []).append(row["symbol"])

    targets: dict[str, list[str]] = {}
    for row in ex_rows:
        name = row["exchange"]
        if name in EXCHANGES:
            targets[name] = symbols_by_ex.get(name, list(DEFAULT_SYMBOLS))
    return targets or {"binance": list(DEFAULT_SYMBOLS)}


async def _sync_pairs() -> None:
    """Синхронизирует tracked_pairs из TRACKED_SYMBOLS env var.

    Для каждой активной биржи загружает markets через CCXT, проверяет
    доступность каждой пары, и делает upsert только существующих пар.
    """
    raw = settings.tracked_symbols
    if not raw:
        return
    desired = [s.strip() for s in raw.split(",") if s.strip()]
    if not desired:
        return

    try:
        pool = await get_db_pool()
        ex_rows = await pool.fetch(
            "SELECT exchange FROM exchange_configs WHERE is_active = true"
        )
    except Exception as err:
        log.warning("sync_pairs_db_unavailable", error=str(err))
        return

    active_exchanges = [r["exchange"] for r in ex_rows if r["exchange"] in EXCHANGES]

    for ex_name in active_exchanges:
        exchange = create_exchange(ex_name)
        try:
            await exchange.load_markets()
            available = set(exchange.markets.keys())
            valid_symbols = [s for s in desired if s in available]
            log.info(
                "sync_pairs_validated",
                exchange=ex_name,
                requested=len(desired),
                available=len(valid_symbols),
                skipped=len(desired) - len(valid_symbols),
            )
            if valid_symbols:
                await pool.executemany(
                    """INSERT INTO tracked_pairs (symbol, exchange, is_active, priority)
                       VALUES ($1, $2, true, 2)
                       ON CONFLICT (symbol, exchange) DO UPDATE SET is_active = true""",
                    [(sym, ex_name) for sym in valid_symbols],
                )
        except Exception as err:
            log.warning("sync_pairs_exchange_error", exchange=ex_name, error=str(err))
        finally:
            try:
                await exchange.close()
            except Exception:
                pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    _state["started_at"] = time.time()

    publisher = RedisPublisher()
    await publisher.connect()
    _state["publisher"] = publisher

    await _sync_pairs()
    targets = await _load_targets()
    collectors = [ExchangeCollector(name, symbols, publisher) for name, symbols in targets.items()]
    for collector in collectors:
        await collector.start()
    _state["collectors"] = collectors

    # BatchWriter — фаза 5; если БД недоступна, продолжаем без записи в БД
    try:
        writer = BatchWriter()
        await writer.start()
        _state["writer"] = writer
    except Exception as err:  # noqa: BLE001
        log.warning("db_writer_disabled", error=str(err))
        _state["writer"] = None

    log.info("collector_up", exchanges=list(targets.keys()))
    try:
        yield
    finally:
        for collector in collectors:
            await collector.stop()
        if _state["writer"] is not None:
            await _state["writer"].stop()
        await publisher.close()
        await close_db_pool()
        log.info("collector_down")


app = FastAPI(title=f"{SERVICE} service", lifespan=lifespan)


def _messages_per_minute(total: int) -> int:
    uptime = max(1.0, time.time() - _state["started_at"])
    return int(total / uptime * 60)


@app.get("/health")
async def health() -> dict:
    collectors: list[ExchangeCollector] = _state["collectors"]
    publisher: RedisPublisher | None = _state["publisher"]
    writer: BatchWriter | None = _state["writer"]

    detail = {c.name: c.status for c in collectors}
    connected = sum(1 for c in collectors if c.status == "connected")
    total_msgs = sum(c.message_count for c in collectors)
    redis_ok = await publisher.ping() if publisher else False

    return {
        "status": "healthy",
        "service": SERVICE,
        "ws_connections": connected,
        "ws_connections_detail": detail,
        "redis_connected": redis_ok,
        "messages_per_minute": _messages_per_minute(total_msgs),
        "db_rows_written": writer.rows_written if writer else 0,
    }


@app.get("/metrics")
async def metrics() -> Response:
    collectors: list[ExchangeCollector] = _state["collectors"]
    _ws_connections_gauge.set(sum(1 for c in collectors if c.status == "connected"))
    _ws_messages_gauge.set(sum(c.message_count for c in collectors))
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
