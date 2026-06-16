"""GET /api/v1/balance — виртуальный баланс по биржам из Redis (Фаза 9)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from auth import get_current_user
from redis_client import get_redis
from shared.config import EXCHANGES

router = APIRouter(prefix="/api/v1", tags=["balance"])


@router.get("/balance")
async def get_balance(_user: str = Depends(get_current_user)) -> dict:
    r = await get_redis()
    items = []
    for exchange in EXCHANGES:
        value = await r.hget(f"balance:{exchange}", "USDT")
        items.append({
            "exchange": exchange,
            "asset": "USDT",
            "amount": float(value) if value is not None else 0.0,
        })
    return {"items": items, "total": round(sum(i["amount"] for i in items), 2)}
