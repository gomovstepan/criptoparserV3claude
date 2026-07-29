"""Виртуальный баланс по биржам в Redis Hash ``balance:{exchange}`` (Фаза 7).

Начальные балансы из ТЗ (раздел 2.4). Учёт ведётся в USDT.
"""
from __future__ import annotations

import asyncpg
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


async def has_any_balance(r: redis.Redis) -> bool:
    """Есть ли в Redis хоть один живой баланс (отличает «пусто» от «нулевой»)."""
    pipe = r.pipeline()
    for exchange in INITIAL_BALANCES_USDT:
        pipe.hget(_key(exchange), "USDT")
    return any(value is not None for value in await pipe.execute())


async def restore_balances(r: redis.Redis, pool: asyncpg.Pool) -> None:
    """Восстановить отсутствующие в Redis балансы из hypertable ``balance``.

    Redis — рабочая копия, PG-ledger — история. После потери ключей (flush,
    пересоздание тома, ранее — eviction) баланс продолжается с последнего
    значения ledger, а не с INITIAL_BALANCES_USDT: повторный сид стартового
    капитала поверх накопленной истории исказил бы P&L. HSETNX — живые
    значения в Redis никогда не перетираются.
    """
    rows = await pool.fetch(
        "SELECT DISTINCT ON (exchange) exchange, amount FROM balance "
        "WHERE asset = 'USDT' ORDER BY exchange, time DESC"
    )
    # Один MULTI/EXEC вместо N раздельных HSETNX: обрыв соединения посреди
    # цикла восстановил бы ЧАСТЬ бирж — has_any_balance в вызывающем коде
    # увидел бы «балансы есть», не взвёл kill switch, и init_balances молча
    # засеял бы остальным биржам стартовый капитал поверх реальной истории.
    pipe = r.pipeline()
    queued = 0
    for row in rows:
        if row["exchange"] in INITIAL_BALANCES_USDT:
            pipe.hsetnx(_key(row["exchange"]), "USDT", float(row["amount"]))
            queued += 1
    if queued:
        await pipe.execute()


async def get_balance(r: redis.Redis, exchange: str) -> float:
    value = await r.hget(_key(exchange), "USDT")
    return float(value) if value is not None else 0.0


async def update_balance(r: redis.Redis, exchange: str, delta: float) -> float:
    """Изменить баланс USDT на ``delta`` и вернуть новое значение."""
    return float(await r.hincrbyfloat(_key(exchange), "USDT", delta))


async def all_balances(r: redis.Redis) -> dict[str, float]:
    return {ex: await get_balance(r, ex) for ex in INITIAL_BALANCES_USDT}
