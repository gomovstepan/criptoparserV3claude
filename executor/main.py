"""Executor (порт 8003) — paper trading engine (Фаза 7).

Читает opportunities из Redis Stream ``opportunities`` (consumer group
``executor-cg``), симулирует сделки, пишет их в hypertable ``trades`` и Redis
Stream ``trades``, обновляет виртуальные балансы (Redis Hash + hypertable
``balance``). Kill switch (``POST /killswitch``) останавливает торговлю.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal

import redis.asyncio as redis
import structlog
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from pydantic import BaseModel

from balance import all_balances, init_balances
from paper_trading import ExecutionResult, PaperTradingEngine
from shared.config import settings
from shared.db import close_db_pool, get_db_pool
from shared.logging_config import setup_logging
from shared.models import Opportunity
from shared.redis_utils import wait_until_ready

SERVICE = "executor"
setup_logging(SERVICE)
log = structlog.get_logger()

OPPORTUNITIES_STREAM = "opportunities"
TRADES_STREAM = "trades"
GROUP = "executor-cg"
CONSUMER = "executor-1"
TRADES_MAXLEN = 10_000
KILL_SWITCH_KEY = "executor:kill_switch"
SETTINGS_REFRESH_SEC = 10

_TRADE_COLUMNS = [
    "time", "id", "opportunity_id", "symbol", "buy_exchange", "sell_exchange",
    "buy_price", "sell_price", "amount", "buy_fee", "sell_fee", "withdrawal_fee",
    "slippage_cost", "gross_pnl", "net_pnl", "buy_top_ask", "sell_top_bid",
    "status", "executed_at", "duration_ms",
]
_BALANCE_COLUMNS = ["time", "exchange", "asset", "amount", "trade_id", "change_amount", "reason"]

_pnl_gauge = Gauge("trade_pnl_usd_total", "Суммарный net P&L по сделкам")
_trades_gauge = Gauge("trades_executed_total", "Всего исполнено сделок")

_state: dict = {
    "redis": None, "pool": None, "engine": None,
    "trades_executed": 0, "loop_errors": 0,
    "task": None, "refresher": None, "running": False,
}


def _D(value: float | str | Decimal) -> Decimal:
    return Decimal(str(value))


def _setting_float(raw: str | float | None, fallback: float) -> float:
    """JSONB-значение из settings (``"10.00"`` или ``10.0``) → float."""
    try:
        return float(str(raw).strip('"'))
    except (TypeError, ValueError):
        return fallback


# settings-ключ → атрибут PaperTradingEngine (одно место для refresher'а и lifespan).
_ENGINE_SETTINGS = {
    "max_position_pct": "max_position_pct",
    "rebalance_threshold_usd": "rebalance_threshold",
    "min_profit_usd": "min_profit_usd",
    "loss_cooldown_sec": "loss_cooldown_sec",
    "depth_max_age_ms_executor": "depth_max_age_ms",
}


async def _apply_engine_settings(engine: PaperTradingEngine) -> None:
    """Считать все настройки движка из таблицы settings (терпимо к мусору)."""
    rows = await _state["pool"].fetch(
        "SELECT key, value FROM settings WHERE key = ANY($1::text[])",
        list(_ENGINE_SETTINGS),
    )
    for row in rows:
        attr = _ENGINE_SETTINGS[row["key"]]
        setattr(engine, attr, _setting_float(row["value"], getattr(engine, attr)))


async def _refresh_settings() -> None:
    """Периодически перечитывать настройки движка из таблицы settings.

    По образцу ``scanner/main.py::_refresh_min_spread``. До этого величины
    замораживались в ``lifespan`` на старте, и правка в UI применялась только
    после перезапуска контейнера — при том что дашборд показывал «Сохранено».
    Парсинг терпимый: битое значение оставляет прежнее, а не роняет executor.
    """
    while _state["running"]:
        try:
            await _apply_engine_settings(_state["engine"])
        except Exception as err:  # noqa: BLE001
            log.warning("settings_refresh_failed", error=str(err))
        await asyncio.sleep(SETTINGS_REFRESH_SEC)


async def _ensure_group(r: redis.Redis) -> None:
    try:
        await r.xgroup_create(OPPORTUNITIES_STREAM, GROUP, id="$", mkstream=True)
    except redis.ResponseError as err:
        if "BUSYGROUP" not in str(err):
            raise


async def _seed_initial_balance_history(pool) -> None:
    """Записать начальные балансы в hypertable balance один раз (на пустой таблице)."""
    count = await pool.fetchval("SELECT count(*) FROM balance")
    if count and count > 0:
        return
    from balance import INITIAL_BALANCES_USDT
    now = datetime.now(tz=timezone.utc)
    records = [
        (now, ex, "USDT", _D(amt), None, _D(amt), "initial")
        for ex, amt in INITIAL_BALANCES_USDT.items()
    ]
    await pool.copy_records_to_table("balance", records=records, columns=_BALANCE_COLUMNS)


def _trade_record(t) -> tuple:
    executed = datetime.fromtimestamp(t.executed_at / 1000, tz=timezone.utc)
    return (
        executed, t.id, t.opportunity_id, t.symbol, t.buy_exchange, t.sell_exchange,
        _D(t.buy_price), _D(t.sell_price), _D(t.amount), _D(t.buy_fee), _D(t.sell_fee),
        _D(t.withdrawal_fee), _D(t.slippage_cost), _D(t.gross_pnl), _D(t.net_pnl),
        _D(t.buy_top_ask) if t.buy_top_ask is not None else None,
        _D(t.sell_top_bid) if t.sell_top_bid is not None else None,
        t.status, executed, t.duration_ms,
    )


async def _insert_rows_fallback(con, table: str, columns: list[str], records: list[tuple]) -> None:
    """Построчный INSERT после упавшего COPY; битые строки логируются и пропускаются.

    ``table``/``columns`` — только модульные константы, не данные.
    """
    cols = ", ".join(columns)
    ph = ", ".join(f"${i + 1}" for i in range(len(columns)))
    for rec in records:
        try:
            await con.execute(f"INSERT INTO {table} ({cols}) VALUES ({ph})", *rec)
        except Exception as row_err:  # noqa: BLE001
            log.error("persist_row_failed", table=table,
                      error=str(row_err), row_key=str(rec[1]))


async def _persist(results: list[ExecutionResult]) -> None:
    pool, r = _state["pool"], _state["redis"]
    trade_records, balance_records = [], []
    for res in results:
        t = res.trade
        # t=None: сделка не состоялась, но ребаланс уже подвинул Redis —
        # его строки ниже всё равно обязаны попасть в hypertable.
        if t is not None:
            trade_records.append(_trade_record(t))
            executed = datetime.fromtimestamp(t.executed_at / 1000, tz=timezone.utc)
            for exchange, new_balance, change in res.balance_updates:
                balance_records.append(
                    (executed, exchange, "USDT", _D(new_balance), t.id, _D(change), "trade")
                )
        else:
            executed = datetime.now(tz=timezone.utc)
        if res.rebalance:
            rb = res.rebalance
            # Клампим так же, как записи сделок ниже: в hypertable висит
            # CHECK (amount >= 0), и отрицательный баланс уронил бы весь COPY.
            balance_records.append(
                (executed, rb.donor, "USDT", _D(max(0.0, rb.donor_new_balance)), None, _D(-rb.gross_amount), "rebalance")
            )
            balance_records.append(
                (executed, rb.receiver, "USDT", _D(max(0.0, rb.receiver_new_balance)), None, _D(rb.net_amount), "rebalance")
            )
    # Обе таблицы пишутся в ОДНОЙ транзакции. Раньше это были два независимых
    # COPY на пуле: падение второго оставляло сделки без соответствующей истории
    # балансов — при том что балансы в Redis уже изменены и откату не подлежат.
    if trade_records or balance_records:
        try:
            async with pool.acquire() as con, con.transaction():
                if trade_records:
                    await con.copy_records_to_table("trades", records=trade_records, columns=_TRADE_COLUMNS)
                if balance_records:
                    await con.copy_records_to_table("balance", records=balance_records, columns=_BALANCE_COLUMNS)
        except Exception as err:  # noqa: BLE001
            # Fallback по строкам, как в collector/db_writer: одна плохая запись
            # не должна терять весь батч — балансы в Redis уже сдвинуты, и каждая
            # спасённая строка уменьшает расхождение ledger'а с Redis.
            log.error("persist_copy_failed_row_fallback", error=str(err),
                      trades=len(trade_records), balances=len(balance_records))
            async with pool.acquire() as con:
                await _insert_rows_fallback(con, "trades", _TRADE_COLUMNS, trade_records)
                await _insert_rows_fallback(con, "balance", _BALANCE_COLUMNS, balance_records)
    for res in results:
        if res.trade is not None:
            await r.xadd(TRADES_STREAM, res.trade.to_redis(), maxlen=TRADES_MAXLEN, approximate=True)


async def _consume_loop() -> None:
    r: redis.Redis = _state["redis"]
    engine: PaperTradingEngine = _state["engine"]
    while _state["running"]:
        try:
            resp = await r.xreadgroup(GROUP, CONSUMER, {OPPORTUNITIES_STREAM: ">"}, count=100, block=1000)
            if not resp:
                continue
            _, entries = resp[0]
            ids, results = [], []
            try:
                for msg_id, fields in entries:
                    ids.append(msg_id)
                    # Kill switch перечитывается ПЕРЕД каждой возможностью, а не раз
                    # на батч: иначе после переключения из дашборда успевал исполниться
                    # весь уже вычитанный батч — до 100 сделок после «Остановить».
                    engine.kill_switch = (await r.get(KILL_SWITCH_KEY)) == "1"
                    if engine.kill_switch:
                        continue
                    try:
                        opp = Opportunity.from_redis(fields)
                    except Exception:  # noqa: BLE001
                        continue
                    # Изоляция per-message: исключение одной возможности не должно
                    # ронять батч — балансы уже исполненных сделок сдвинуты в Redis,
                    # и их результаты обязаны дожить до _persist ниже.
                    try:
                        res = await engine.execute_opportunity(opp)
                    except Exception as err:  # noqa: BLE001
                        _state["loop_errors"] += 1
                        log.error("execute_opportunity_failed", error=str(err),
                                  opportunity_id=fields.get("id", "?"))
                        continue
                    if res is not None:
                        results.append(res)
            finally:
                # Персист — в finally: даже если что-то выше бросило после N
                # исполненных сообщений, их движения балансов уже в Redis, и
                # потеря results означала бы молчаливое расхождение ledger'а.
                if results:
                    try:
                        await _persist(results)
                        _state["trades_executed"] += sum(
                            1 for res in results if res.trade is not None
                        )
                    except Exception as err:  # noqa: BLE001
                        _state["loop_errors"] += 1
                        log.error("persist_failed", error=str(err), results=len(results))
                # ACK безусловный. xreadgroup читает только ">", а XAUTOCLAIM/XPENDING
                # в системе нет — без этого записи упавшего батча остались бы в PEL
                # навсегда. Переотправку добавлять НЕЛЬЗЯ: HINCRBYFLOAT балансов не
                # идемпотентен, повторная обработка удвоила бы движение средств.
                if ids:
                    await r.xack(OPPORTUNITIES_STREAM, GROUP, *ids)
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            _state["loop_errors"] += 1
            log.error("executor_loop_error", error=str(err), loop_errors=_state["loop_errors"])
            await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    r = redis.from_url(settings.redis_url, decode_responses=True)
    await wait_until_ready(r)
    pool = await get_db_pool()
    _state["redis"], _state["pool"] = r, pool

    await init_balances(r)
    await _seed_initial_balance_history(pool)
    await _ensure_group(r)

    engine = PaperTradingEngine(r)
    try:
        await _apply_engine_settings(engine)
    except Exception as err:  # noqa: BLE001
        log.warning("engine_settings_load_failed", error=str(err))
    engine.kill_switch = (await r.get(KILL_SWITCH_KEY)) == "1"
    _state["engine"] = engine

    if settings.paper:
        _state["running"] = True
        _state["task"] = asyncio.create_task(_consume_loop(), name="executor_loop")
        _state["refresher"] = asyncio.create_task(_refresh_settings(), name="settings_refresher")
        log.info("executor_up", mode="paper",
                 max_position_pct=engine.max_position_pct, kill_switch=engine.kill_switch)
    else:
        # Реальная торговля не реализована: executor не подписывается на opportunities.
        # Балансы и kill switch остаются доступны, но сделки не создаются.
        log.warning("executor_idle", mode="real",
                    reason="real trading not implemented; set PAPER=true to enable simulation")
    try:
        yield
    finally:
        _state["running"] = False
        for key in ("task", "refresher"):
            if _state[key] is not None:
                _state[key].cancel()
                await asyncio.gather(_state[key], return_exceptions=True)
        await r.aclose()
        await close_db_pool()
        log.info("executor_down")


app = FastAPI(title=f"{SERVICE} service", lifespan=lifespan)


class KillSwitchRequest(BaseModel):
    reason: str = "manual"
    active: bool = True


@app.post("/killswitch")
async def killswitch(req: KillSwitchRequest) -> dict:
    engine: PaperTradingEngine = _state["engine"]
    engine.kill_switch = req.active
    await _state["redis"].set(KILL_SWITCH_KEY, "1" if req.active else "0")
    log.warning("kill_switch_changed", active=req.active, reason=req.reason)
    return {
        "status": "activated" if req.active else "deactivated",
        "reason": req.reason,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "kill_switch_active": req.active,
    }


@app.get("/health")
async def health() -> dict:
    engine: PaperTradingEngine = _state["engine"]
    pool = _state["pool"]
    trades_today = total_pnl = 0
    try:
        row = await pool.fetchrow(
            "SELECT count(*) AS n, COALESCE(sum(net_pnl), 0) AS pnl "
            "FROM trades WHERE time >= date_trunc('day', now())"
        )
        reb_fee = await pool.fetchval(
            "SELECT COALESCE(sum(change_amount), 0) FROM balance "
            "WHERE reason = 'rebalance' AND time >= date_trunc('day', now())"
        )
        trades_today, total_pnl = int(row["n"]), float(row["pnl"]) + float(reb_fee)
    except Exception:  # noqa: BLE001
        pass
    return {
        "status": "healthy",
        "service": SERVICE,
        "paper": settings.paper,
        "trades_today": trades_today,
        "total_pnl_today": round(total_pnl, 2),
        "kill_switch_active": engine.kill_switch if engine else False,
        # Живые значения из refresher'а — по ним видно, что правка в UI доехала.
        "max_position_pct": engine.max_position_pct if engine else None,
        "rebalance_threshold_usd": engine.rebalance_threshold if engine else None,
        "min_profit_usd": engine.min_profit_usd if engine else None,
        "loss_cooldown_sec": engine.loss_cooldown_sec if engine else None,
        "depth_max_age_ms_executor": engine.depth_max_age_ms if engine else None,
        "loop_errors": _state["loop_errors"],
        "balances": {k: round(v, 2) for k, v in (await all_balances(_state["redis"])).items()},
    }


@app.get("/metrics")
async def metrics() -> Response:
    _trades_gauge.set(_state["trades_executed"])
    # Инвариант PNL_EVENTS: sum(trades.net_pnl) + sum(rebalance-движений).
    # Раньше gauge объявлялся, но никогда не выставлялся — вечный 0.
    try:
        pnl = await _state["pool"].fetchval(
            "SELECT COALESCE((SELECT sum(net_pnl) FROM trades), 0) "
            "+ COALESCE((SELECT sum(change_amount) FROM balance WHERE reason='rebalance'), 0)"
        )
        _pnl_gauge.set(float(pnl or 0))
    except Exception:  # noqa: BLE001
        pass
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
