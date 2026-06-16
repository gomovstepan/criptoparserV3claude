"""GET /api/v1/prices — последние цены из TimescaleDB (Фаза 9)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from auth import get_current_user
from shared.db import get_db_pool

router = APIRouter(prefix="/api/v1", tags=["prices"])


@router.get("/prices")
async def get_prices(
    symbol: str | None = None,
    exchange: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    _user: str = Depends(get_current_user),
) -> dict:
    clauses, params = [], []
    if symbol:
        params.append(symbol)
        clauses.append(f"symbol = ${len(params)}")
    if exchange:
        params.append(exchange)
        clauses.append(f"exchange = ${len(params)}")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)

    pool = await get_db_pool()
    rows = await pool.fetch(
        f"SELECT time, exchange, symbol, bid, ask, bid_volume, ask_volume "
        f"FROM prices {where} ORDER BY time DESC LIMIT ${len(params)}",
        *params,
    )
    items = [
        {
            "time": r["time"].isoformat(),
            "exchange": r["exchange"],
            "symbol": r["symbol"],
            "bid": float(r["bid"]),
            "ask": float(r["ask"]),
            "bid_volume": float(r["bid_volume"]) if r["bid_volume"] is not None else None,
            "ask_volume": float(r["ask_volume"]) if r["ask_volume"] is not None else None,
        }
        for r in rows
    ]
    return {"items": items, "total": len(items)}
