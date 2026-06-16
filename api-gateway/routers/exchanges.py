"""GET /api/v1/exchanges, /exchanges/status и GET/PUT /api/v1/settings (Фазы 9, 11)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from shared.config import EXCHANGES
from shared.db import get_db_pool

router = APIRouter(prefix="/api/v1", tags=["exchanges"])

CONNECTED_THRESHOLD_SEC = 15


@router.get("/exchanges")
async def get_exchanges(_user: str = Depends(get_current_user)) -> dict:
    pool = await get_db_pool()
    rows = await pool.fetch(
        "SELECT exchange, is_active, maker_fee_pct, taker_fee_pct, withdrawal_btc, "
        "withdrawal_usdt, rate_limit_req_per_sec FROM exchange_configs ORDER BY id"
    )
    items = [
        {
            "exchange": r["exchange"],
            "is_active": r["is_active"],
            "maker_fee_pct": float(r["maker_fee_pct"]),
            "taker_fee_pct": float(r["taker_fee_pct"]),
            "withdrawal_btc": float(r["withdrawal_btc"]) if r["withdrawal_btc"] is not None else None,
            "withdrawal_usdt": float(r["withdrawal_usdt"]) if r["withdrawal_usdt"] is not None else None,
            "rate_limit_req_per_sec": r["rate_limit_req_per_sec"],
        }
        for r in rows
    ]
    return {"items": items, "total": len(items)}


class ExchangeUpdate(BaseModel):
    is_active: bool


@router.patch("/exchanges/{exchange}")
async def update_exchange(
    exchange: str,
    payload: ExchangeUpdate,
    _user: str = Depends(get_current_user),
) -> dict:
    """Включить/выключить биржу (toggle is_active).

    Меняет флаг в `exchange_configs`. Коллектор читает `is_active` при старте,
    поэтому фактическое подключение/отключение применится после его рестарта —
    флаг же сохраняется сразу и виден в списке бирж.
    """
    pool = await get_db_pool()
    row = await pool.fetchrow(
        "UPDATE exchange_configs SET is_active = $1 WHERE exchange = $2 "
        "RETURNING exchange, is_active",
        payload.is_active, exchange,
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"exchange '{exchange}' not found")
    return {"exchange": row["exchange"], "is_active": row["is_active"]}


@router.get("/exchanges/status")
async def get_exchange_status(_user: str = Depends(get_current_user)) -> dict:
    """Статус бирж по свежести последнего тика в TimescaleDB (для дашборда)."""
    pool = await get_db_pool()
    rows = await pool.fetch(
        """
        SELECT DISTINCT ON (exchange) exchange, time, latency_ms
        FROM prices
        WHERE time > now() - interval '2 minutes'
        ORDER BY exchange, time DESC
        """
    )
    latest = {r["exchange"]: r for r in rows}
    now = datetime.now(timezone.utc)
    items = []
    for exchange in EXCHANGES:
        r = latest.get(exchange)
        if r is None:
            items.append({"exchange": exchange, "status": "disconnected", "latency_ms": None, "last_tick": None})
            continue
        age = (now - r["time"]).total_seconds()
        items.append({
            "exchange": exchange,
            "status": "connected" if age < CONNECTED_THRESHOLD_SEC else "stale",
            "latency_ms": r["latency_ms"],
            "last_tick": r["time"].isoformat(),
        })
    return {"items": items}


def _parse_setting(raw: str):
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


@router.get("/settings")
async def get_settings(_user: str = Depends(get_current_user)) -> dict:
    pool = await get_db_pool()
    rows = await pool.fetch("SELECT key, value FROM settings")
    return {r["key"]: _parse_setting(r["value"]) for r in rows}


@router.put("/settings")
async def update_settings(
    payload: dict = Body(...),
    _user: str = Depends(get_current_user),
) -> dict:
    pool = await get_db_pool()
    for key, value in payload.items():
        await pool.execute(
            "UPDATE settings SET value = $1::jsonb, updated_at = now() WHERE key = $2",
            json.dumps(value), key,
        )
    return {"status": "updated", "settings": payload}
