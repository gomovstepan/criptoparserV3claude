"""GET/PUT /api/v1/balance — виртуальный баланс по биржам (Фаза 9 + paper-режим).

PUT доступен только при ``settings.paper=true``: переписывает балансы в Redis Hash
``balance:{exchange}`` (USDT) и фиксирует изменение в hypertable ``balance`` с
``reason='adjustment'`` — чтобы изменение было видно в истории как отдельное
событие, аналогично seed'у начальных балансов.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_user
from redis_client import get_redis
from shared.config import EXCHANGES, settings
from shared.db import get_db_pool

router = APIRouter(prefix="/api/v1", tags=["balance"])


class BalanceItem(BaseModel):
    exchange: str
    asset: str
    amount: float


class BalanceList(BaseModel):
    items: list[BalanceItem]
    total: float


class BalanceUpdateResult(BaseModel):
    status: str
    balances: dict[str, float]


@router.get("/balance")
async def get_balance(_user: str = Depends(get_current_user)) -> BalanceList:
    r = await get_redis()
    # Один round-trip вместо HGET на биржу (N+1).
    pipe = r.pipeline()
    for exchange in EXCHANGES:
        pipe.hget(f"balance:{exchange}", "USDT")
    values = await pipe.execute()
    items = [
        {
            "exchange": exchange,
            "asset": "USDT",
            "amount": float(value) if value is not None else 0.0,
        }
        for exchange, value in zip(EXCHANGES, values, strict=True)
    ]
    return {"items": items, "total": round(sum(i["amount"] for i in items), 2)}


class BalanceUpdate(BaseModel):
    """Карта `биржа → новая сумма USDT`. Принимаются только известные биржи.

    ``allow_inf_nan=False``: JSON ``NaN`` проходит json.loads, обходит проверку
    ``v < 0`` (сравнение с NaN всегда False) и валит ``Decimal(str(v))`` ниже
    необработанным 500 — отсекаем его нормальным 422 на валидации.
    """

    balances: dict[str, Annotated[float, Field(allow_inf_nan=False)]] = Field(..., min_length=1)


# NUMERIC(28,8) ⇒ |value| < 10^20, но операционного смысла в балансах такого
# порядка нет — оставляем прежний потолок 1e10 как санитарную границу ввода.
COL_MAX = Decimal("1e10")

# Атомарный swap: прочитать прежний баланс и записать новый ОДНОЙ операцией.
# Раздельные HGET→HSET оставляли окно, в котором HINCRBYFLOAT executor'а
# (движение сделки) молча затирался абсолютной записью оператора, а
# change_amount в ledger'е считался от устаревшего прежнего значения.
_SWAP_LUA = """
local prev = redis.call('HGET', KEYS[1], ARGV[1])
redis.call('HSET', KEYS[1], ARGV[1], ARGV[2])
return prev
"""


@router.put("/balance")
async def set_balances(
    payload: BalanceUpdate,
    _user: str = Depends(get_current_user),
) -> BalanceUpdateResult:
    if not settings.paper:
        raise HTTPException(status_code=403, detail="balances editable only in paper mode")

    unknown = [ex for ex in payload.balances if ex not in EXCHANGES]
    if unknown:
        raise HTTPException(status_code=400, detail=f"unknown exchanges: {unknown}")
    negative = [ex for ex, v in payload.balances.items() if v < 0]
    if negative:
        raise HTTPException(status_code=400, detail=f"negative balances: {negative}")
    too_large = [ex for ex, v in payload.balances.items() if Decimal(str(v)) >= COL_MAX]
    if too_large:
        raise HTTPException(status_code=400, detail=f"balances too large (>= 1e10): {too_large}")

    r = await get_redis()
    pool = await get_db_pool()
    now = datetime.now(tz=timezone.utc)

    records = []
    updated: dict[str, float] = {}
    for exchange, amount in payload.balances.items():
        key = f"balance:{exchange}"
        prev = await r.eval(_SWAP_LUA, 1, key, "USDT", repr(float(amount)))
        prev_f = float(prev) if prev is not None else 0.0
        # Если предыдущий баланс был мусором (e.g. из старого прогона), разница
        # может не поместиться в колонку change_amount — тогда пишем NULL.
        change_dec: Decimal | None = Decimal(str(float(amount) - prev_f))
        if abs(change_dec) >= COL_MAX:
            change_dec = None
        records.append((
            now, exchange, "USDT", Decimal(str(amount)), None,
            change_dec, "adjustment",
        ))
        updated[exchange] = float(amount)

    await pool.copy_records_to_table(
        "balance", records=records,
        columns=["time", "exchange", "asset", "amount", "trade_id", "change_amount", "reason"],
    )
    return {"status": "updated", "balances": updated}
