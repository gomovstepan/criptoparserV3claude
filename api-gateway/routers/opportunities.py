"""GET /api/v1/opportunities — обнаруженные спреды из TimescaleDB (Фаза 9)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from auth import get_current_user
from routers.query_filters import build_filters
from shared.db import get_db_pool

router = APIRouter(prefix="/api/v1", tags=["opportunities"])


class OpportunityOut(BaseModel):
    id: str
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    gross_spread_pct: float
    buy_fee_pct: float
    sell_fee_pct: float
    net_fees_pct: float
    net_spread_pct: float
    detected_at: str


class OpportunitiesResponse(BaseModel):
    items: list[OpportunityOut]
    total: int


@router.get("/opportunities")
async def get_opportunities(
    symbol: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    _user: str = Depends(get_current_user),
) -> OpportunitiesResponse:
    where, params = build_filters(symbol=symbol)
    params.append(limit)

    pool = await get_db_pool()
    rows = await pool.fetch(
        f"SELECT time, id, symbol, buy_exchange, sell_exchange, buy_price, sell_price, "
        f"gross_spread_pct, buy_fee_pct, sell_fee_pct, net_spread_pct "
        f"FROM opportunities {where} "
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
            "buy_fee_pct": float(r["buy_fee_pct"]),
            "sell_fee_pct": float(r["sell_fee_pct"]),
            # Честный net по модели ledger'а: только taker-комиссии обеих ног.
            # net_spread_pct (ниже) дополнительно вычитает комиссию вывода,
            # размазанную на один notional (~40x пессимистичнее фактической),
            # и остаётся display-only — фильтровать по нему нельзя.
            "net_fees_pct": round(
                float(r["gross_spread_pct"]) - float(r["buy_fee_pct"]) - float(r["sell_fee_pct"]), 4,
            ),
            "net_spread_pct": float(r["net_spread_pct"]),
            "detected_at": r["time"].isoformat(),
        }
        for r in rows
    ]
    return {"items": items, "total": len(items)}
