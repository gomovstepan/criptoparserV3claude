"""Доступ к TimescaleDB через пул соединений asyncpg.

Один пул на процесс. ``get_db_pool`` создаёт его лениво с повторными попытками
подключения (БД может стартовать дольше сервиса), ``close_db_pool`` закрывает
при graceful shutdown.
"""
from __future__ import annotations

import asyncio

import asyncpg

from shared.config import settings

_pool: asyncpg.Pool | None = None


async def get_db_pool(retries: int = 5, delay: float = 2.0) -> asyncpg.Pool:
    """Вернуть (создав при необходимости) пул соединений к TimescaleDB."""
    global _pool
    if _pool is not None:
        return _pool

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            _pool = await asyncpg.create_pool(
                dsn=settings.database_dsn,
                min_size=1,
                max_size=10,
                command_timeout=60,
            )
            return _pool
        except (OSError, asyncpg.PostgresError) as err:  # БД ещё не готова
            last_err = err
            if attempt < retries:
                await asyncio.sleep(delay)

    raise RuntimeError(f"Не удалось подключиться к TimescaleDB за {retries} попыток") from last_err


async def close_db_pool() -> None:
    """Закрыть пул соединений (idempotent)."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
