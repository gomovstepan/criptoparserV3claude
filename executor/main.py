"""Executor (порт 8003) — paper trading engine (Фаза 7).

Читает opportunities из Redis Stream ``opportunities`` (consumer group
``executor-cg``), симулирует сделки, пишет их в hypertable ``trades`` и Redis
Stream ``trades``, обновляет виртуальные балансы (Redis Hash + hypertable
``balance``). Kill switch (``POST /killswitch``) останавливает торговлю.
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
from pydantic import BaseModel

from balance import all_balances, init_balances
from paper_trading import ExecutionResult, PaperTradingEngine
from shared.config import settings
from shared.db import close_db_pool, get_db_pool
from shared.models import Opportunity

log = structlog.get_logger()
SERVICE = "executor"

OPPORTUNITIES_STREAM = "opportunities"
TRADES_STREAM = "trades"
GROUP = "executor-cg"
CONSUMER = "executor-1"
TRADES_MAXLEN = 10_000
KILL_SWITCH_KEY = "executor:kill_switch"

_TRADE_COLUMNS = [
    "time", "id", "opportunity_id", "symbol", "buy_exchange", "sell_exchange",
    "buy_price", "sell_price", "amount", "buy_fee", "sell_fee", "withdrawal_fee",
    "slippage_cost", "gross_pnl", "net_pnl", "status", "executed_at", "duration_ms",
]
_BALANCE_COLUMNS = ["time", "exchange", "asset", "amount", "trade_id", "change_amount", "reason"]

_pnl_gauge = Gauge("trade_pnl_usd_total", "Суммарный net P&L по сделкам")
_trades_gauge = Gauge("trades_executed_total", "Всего исполнено сделок")

_state: dict = {
    "redis": None, "pool": None, "engine": None,
    "trades_executed": 0, "task": None, "running": False,
}


def _D(value) -> Decimal:
    return Decimal(str(value))


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
        t.status, executed, t.duration_ms,
    )


async def _persist(results: list[ExecutionResult]) -> None:
    pool, r = _state["pool"], _state["redis"]
    trade_records, balance_records = [], []
    for res in results:
        t = res.trade
        trade_records.append(_trade_record(t))
        executed = datetime.fromtimestamp(t.executed_at / 1000, tz=timezone.utc)
        for exchange, new_balance, change in res.balance_updates:
            balance_records.append(
                (executed, exchange, "USDT", _D(new_balance), t.id, _D(change), "trade")
            )
    if trade_records:
        await pool.copy_records_to_table("trades", records=trade_records, columns=_TRADE_COLUMNS)
    if balance_records:
        await pool.copy_records_to_table("balance", records=balance_records, columns=_BALANCE_COLUMNS)
    for res in results:
        await r.xadd(TRADES_STREAM, res.trade.to_redis(), maxlen=TRADES_MAXLEN, approximate=True)


async def _consume_loop() -> None:
    r: redis.Redis = _state["redis"]
    engine: PaperTradingEngine = _state["engine"]
    while _state["running"]:
        try:
            # Подхватываем актуальное состояние kill switch из Redis (управляется
            # из API Gateway) — переключение применяется на следующей итерации.
            engine.kill_switch = (await r.get(KILL_SWITCH_KEY)) == "1"
            resp = await r.xreadgroup(GROUP, CONSUMER, {OPPORTUNITIES_STREAM: ">"}, count=100, block=1000)
            if not resp:
                continue
            _, entries = resp[0]
            ids, results = [], []
            for msg_id, fields in entries:
                ids.append(msg_id)
                try:
                    opp = Opportunity.from_redis(fields)
                except Exception:  # noqa: BLE001
                    continue
                res = await engine.execute_opportunity(opp)
                if res is not None:
                    results.append(res)
            if results:
                await _persist(results)
                _state["trades_executed"] += len(results)
            if ids:
                await r.xack(OPPORTUNITIES_STREAM, GROUP, *ids)
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            log.error("executor_loop_error", error=str(err))
            await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    r = redis.from_url(settings.redis_url, decode_responses=True)
    await r.ping()
    pool = await get_db_pool()
    _state["redis"], _state["pool"] = r, pool

    await init_balances(r)
    await _seed_initial_balance_history(pool)
    await _ensure_group(r)

    max_pos = await pool.fetchval("SELECT value FROM settings WHERE key='max_position_pct'")
    engine = PaperTradingEngine(r, max_position_pct=float(str(max_pos).strip('"')) if max_pos else 10.0)
    engine.kill_switch = (await r.get(KILL_SWITCH_KEY)) == "1"
    _state["engine"] = engine

    _state["running"] = True
    _state["task"] = asyncio.create_task(_consume_loop(), name="executor_loop")
    log.info("executor_up", max_position_pct=engine.max_position_pct, kill_switch=engine.kill_switch)
    try:
        yield
    finally:
        _state["running"] = False
        if _state["task"] is not None:
            _state["task"].cancel()
            await asyncio.gather(_state["task"], return_exceptions=True)
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
        trades_today, total_pnl = int(row["n"]), float(row["pnl"])
    except Exception:  # noqa: BLE001
        pass
    return {
        "status": "healthy",
        "service": SERVICE,
        "trades_today": trades_today,
        "total_pnl_today": round(total_pnl, 2),
        "kill_switch_active": engine.kill_switch if engine else False,
        "balances": {k: round(v, 2) for k, v in (await all_balances(_state["redis"])).items()},
    }


@app.get("/metrics")
async def metrics() -> Response:
    _trades_gauge.set(_state["trades_executed"])
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
