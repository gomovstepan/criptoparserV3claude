"""Виртуальный баланс по биржам в Redis Hash ``balance:{exchange}`` (Фаза 7).

Начальные балансы из ТЗ (раздел 2.4). Учёт ведётся в USDT.
"""
from __future__ import annotations

import redis.asyncio as redis

INITIAL_BALANCES_USDT: dict[str, float] = {
    "binance": 10_000,
    "bybit": 10_000,
    "kucoin": 10_000,
    "bitget": 10_000,
    "gateio": 5_000,
    "coinex": 5_000,
    "bingx": 5_000,
}


def _key(exchange: str) -> str:
    return f"balance:{exchange}"


async def init_balances(r: redis.Redis) -> None:
    """Проставить начальные балансы там, где их ещё нет (idempotent)."""
    for exchange, amount in INITIAL_BALANCES_USDT.items():
        await r.hsetnx(_key(exchange), "USDT", amount)


async def get_balance(r: redis.Redis, exchange: str) -> float:
    value = await r.hget(_key(exchange), "USDT")
    return float(value) if value is not None else 0.0


async def update_balance(r: redis.Redis, exchange: str, delta: float) -> float:
    """Изменить баланс USDT на ``delta`` и вернуть новое значение."""
    return float(await r.hincrbyfloat(_key(exchange), "USDT", delta))


async def all_balances(r: redis.Redis) -> dict[str, float]:
    return {ex: await get_balance(r, ex) for ex in INITIAL_BALANCES_USDT}
