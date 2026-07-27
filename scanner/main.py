"""Scanner (порт 8002) — расчёт межбиржевых спредов (Фаза 6).

Читает цены из Redis Stream ``prices`` (consumer group ``scanner-cg``), держит в
памяти последний bid/ask по каждой (бирже, паре), считает спреды между всеми
биржами, фильтрует по ``min_spread`` (из настроек БД), дедуплицирует и публикует
opportunities в Redis Stream ``opportunities`` + пишет в hypertable ``opportunities``.
"""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal

import redis.asyncio as redis
import structlog
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

from dedup import OpportunityDedup
from shared.config import settings
from shared.db import close_db_pool, get_db_pool
from shared.depth import depth_key, is_fresh, parse_depth
from shared.logging_config import setup_logging
from shared.models import Opportunity
from shared.redis_utils import wait_until_ready
from spread_calculator import calculate_spreads

SERVICE = "scanner"
setup_logging(SERVICE)
log = structlog.get_logger()

PRICES_STREAM = "prices"
OPPORTUNITIES_STREAM = "opportunities"
GROUP = "scanner-cg"
CONSUMER = "scanner-1"
OPP_MAXLEN = 10_000
MIN_SPREAD_REFRESH_SEC = 10
# In-memory котировка старше этого — мусор: биржа отвалилась, её замёрзшая
# цена не должна участвовать в расчёте спредов (и порождать фантомы).
PRICE_MAX_AGE_MS = 5_000

_OPP_COLUMNS = [
    "time", "id", "symbol", "buy_exchange", "sell_exchange", "buy_price",
    "sell_price", "gross_spread_pct", "buy_fee_pct", "sell_fee_pct",
    "withdrawal_fee_usd", "net_spread_pct",
]

_spreads_gauge = Gauge("spreads_scanned_total", "Всего рассчитано спредов")
_opps_gauge = Gauge("opportunities_found_total", "Всего найдено возможностей")

_state: dict = {
    "redis": None,
    "pool": None,
    "dedup": None,
    "prices": {},                # symbol -> exchange -> {"bid":.., "ask":.., "ts":..}
    "min_spread": 0.30,
    "min_net_spread": 0.10,
    "estimated_notional": 1000.0,
    "depth_max_age_ms": 3000.0,  # порог свежести глубины ДЛЯ СКАНЕРА (см. settings)
    "spreads_calculated": 0,
    "opportunities_found": 0,
    "started_at": 0.0,
    "task": None,
    "refresher": None,
    "running": False,
}


async def _ensure_group(r: redis.Redis) -> None:
    try:
        await r.xgroup_create(PRICES_STREAM, GROUP, id="$", mkstream=True)
    except redis.ResponseError as err:
        if "BUSYGROUP" not in str(err):
            raise


# settings-ключ → ключ _state (перечитываются каждые MIN_SPREAD_REFRESH_SEC).
_SCANNER_SETTINGS = {
    "min_spread_pct": "min_spread",
    "min_net_spread_pct": "min_net_spread",
    "estimated_trade_notional": "estimated_notional",
    "depth_max_age_ms_scanner": "depth_max_age_ms",
}


async def _refresh_min_spread() -> None:
    """Периодически перечитывать пороги сканера из таблицы settings.

    Парсинг терпимый: битое значение оставляет прежнее, а не роняет сервис.
    """
    while _state["running"]:
        try:
            rows = await _state["pool"].fetch(
                "SELECT key, value FROM settings WHERE key = ANY($1::text[])",
                list(_SCANNER_SETTINGS),
            )
            for row in rows:
                try:
                    _state[_SCANNER_SETTINGS[row["key"]]] = float(str(row["value"]).strip('"'))
                except (TypeError, ValueError):
                    continue
        except Exception as err:  # noqa: BLE001
            log.warning("settings_refresh_failed", error=str(err))
        await asyncio.sleep(MIN_SPREAD_REFRESH_SEC)


def _opp_record(opp: Opportunity) -> tuple:
    return (
        datetime.fromtimestamp(opp.detected_at / 1000, tz=timezone.utc),
        opp.id, opp.symbol, opp.buy_exchange, opp.sell_exchange,
        Decimal(str(opp.buy_price)), Decimal(str(opp.sell_price)),
        Decimal(str(opp.gross_spread_pct)), Decimal(str(opp.buy_fee_pct)),
        Decimal(str(opp.sell_fee_pct)), Decimal(str(opp.withdrawal_fee_usd)),
        Decimal(str(opp.net_spread_pct)),
    )


async def _publish_and_store(opps: list[Opportunity]) -> None:
    r: redis.Redis = _state["redis"]
    dedup: OpportunityDedup = _state["dedup"]
    for opp in opps:
        await r.xadd(OPPORTUNITIES_STREAM, opp.to_redis(), maxlen=OPP_MAXLEN, approximate=True)
        # Отметка сразу после XADD (а не после COPY): публикация в стрим —
        # то, что дедуплицируется. Иначе падение COPY при живом стриме
        # перепубликовывало бы те же возможности каждый тик без троттлинга.
        await dedup.mark(opp)
    records = [_opp_record(o) for o in opps]
    await _state["pool"].copy_records_to_table("opportunities", records=records, columns=_OPP_COLUMNS)


async def _scan_loop() -> None:
    r: redis.Redis = _state["redis"]
    dedup: OpportunityDedup = _state["dedup"]
    prices: dict = _state["prices"]

    while _state["running"]:
        try:
            resp = await r.xreadgroup(GROUP, CONSUMER, {PRICES_STREAM: ">"}, count=300, block=1000)
            if not resp:
                continue
            _, entries = resp[0]
            now_ms = int(time.time() * 1000)
            updated: set[str] = set()
            ids = []
            for msg_id, f in entries:
                ids.append(msg_id)
                try:
                    sym, ex = f["symbol"], f["exchange"]
                    try:
                        ts = int(f["received_at"])
                    except (KeyError, ValueError):
                        ts = now_ms
                    prices.setdefault(sym, {})[ex] = {
                        "bid": float(f["bid"]), "ask": float(f["ask"]), "ts": ts,
                    }
                    updated.add(sym)
                except (KeyError, ValueError):
                    continue

            found: list[Opportunity] = []
            for sym in updated:
                book = prices[sym]
                # Выселяем замёрзшие котировки: отвалившаяся биржа не должна
                # вечно участвовать в спредах последней увиденной ценой.
                for ex in [e for e, q in book.items()
                           if now_ms - q.get("ts", 0) > PRICE_MAX_AGE_MS]:
                    del book[ex]
                n = len(book)
                _state["spreads_calculated"] += n * (n - 1)
                keys = [depth_key(ex, sym) for ex in book]
                raws = await r.mget(keys) if keys else []
                depth_by_ex: dict[str, dict] = {}
                for ex, raw in zip(book.keys(), raws, strict=True):
                    parsed = parse_depth(raw)
                    if is_fresh(parsed, now_ms, _state["depth_max_age_ms"]):
                        depth_by_ex[ex] = parsed
                for opp in calculate_spreads(
                    sym, book, _state["min_spread"], _state["estimated_notional"],
                    depth=depth_by_ex,
                    min_net_spread_pct=_state["min_net_spread"],
                ):
                    if not await dedup.seen(opp):
                        found.append(opp)

            try:
                if found:
                    await _publish_and_store(found)
                    _state["opportunities_found"] += len(found)
            finally:
                # ACK в finally: без него сообщения упавшего батча оседали бы
                # в PEL навсегда (читаем только ">", реклейма нет), а потеря
                # тика цены безвредна — следующий придёт через мгновение.
                if ids:
                    await r.xack(PRICES_STREAM, GROUP, *ids)
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            log.error("scan_loop_error", error=str(err))
            await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _state["started_at"] = time.time()
    _state["redis"] = redis.from_url(settings.redis_url, decode_responses=True)
    await wait_until_ready(_state["redis"])
    _state["pool"] = await get_db_pool()
    _state["dedup"] = OpportunityDedup(_state["redis"], ttl=5)
    await _ensure_group(_state["redis"])

    _state["running"] = True
    _state["task"] = asyncio.create_task(_scan_loop(), name="scan_loop")
    _state["refresher"] = asyncio.create_task(_refresh_min_spread(), name="min_spread_refresher")
    log.info("scanner_up")
    try:
        yield
    finally:
        _state["running"] = False
        for key in ("task", "refresher"):
            if _state[key] is not None:
                _state[key].cancel()
                await asyncio.gather(_state[key], return_exceptions=True)
        await _state["redis"].aclose()
        await close_db_pool()
        log.info("scanner_down")


app = FastAPI(title=f"{SERVICE} service", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    uptime = max(1.0, time.time() - _state["started_at"])
    last_hour = 0
    try:
        last_hour = await _state["pool"].fetchval(
            "SELECT count(*) FROM opportunities WHERE time > now() - interval '1 hour'"
        )
    except Exception:  # noqa: BLE001
        pass
    redis_ok = False
    try:
        redis_ok = bool(await _state["redis"].ping())
    except Exception:  # noqa: BLE001
        pass
    return {
        "status": "healthy",
        "service": SERVICE,
        "spreads_calculated_per_minute": int(_state["spreads_calculated"] / uptime * 60),
        "opportunities_found_total": _state["opportunities_found"],
        "opportunities_found_last_hour": int(last_hour or 0),
        "min_spread_pct": _state["min_spread"],
        "min_net_spread_pct": _state["min_net_spread"],
        "depth_max_age_ms_scanner": _state["depth_max_age_ms"],
        "redis_connected": redis_ok,
    }


@app.get("/metrics")
async def metrics() -> Response:
    _spreads_gauge.set(_state["spreads_calculated"])
    _opps_gauge.set(_state["opportunities_found"])
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
