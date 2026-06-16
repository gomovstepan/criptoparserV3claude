"""GET /api/v1/opportunities — обнаруженные спреды из TimescaleDB (Фаза 9)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from auth import get_current_user
from shared.db import get_db_pool

router = APIRouter(prefix="/api/v1", tags=["opportunities"])


@router.get("/opportunities")
async def get_opportunities(
    symbol: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    _user: str = Depends(get_current_user),
) -> dict:
    clauses, params = [], []
    if symbol:
        params.append(symbol)
        clauses.append(f"symbol = ${len(params)}")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)

    pool = await get_db_pool()
    rows = await pool.fetch(
        f"SELECT time, id, symbol, buy_exchange, sell_exchange, buy_price, sell_price, "
        f"gross_spread_pct, net_spread_pct FROM opportunities {where} "
        f"ORDER BY time DESC LIMIT ${len(params)}",
        *params,
    )
    items = [
        {
            "id": r["id"],
            "symbol": r["symbol"],
            "buy_exchange": r["buy_exchange"],
            "sell_exchange": r["sell_exchange"],
            "buy_price": float(r["buy_price"]),
            "sell_price": float(r["sell_price"]),
            "gross_spread_pct": float(r["gross_spread_pct"]),
            "net_spread_pct": float(r["net_spread_pct"]),
            "detected_at": r["time"].isoformat(),
        }
        for r in rows
    ]
    return {"items": items, "total": len(items)}
