"""Утилиты для работы с Redis."""
from __future__ import annotations

import asyncio

import redis.asyncio as redis
import structlog

log = structlog.get_logger()


async def wait_until_ready(client: redis.Redis, timeout: float = 60.0, interval: float = 1.0) -> None:
    """Ждать, пока Redis закончит загрузку датасета (AOF/RDB).

    После старта контейнера Redis принимает соединения, но возвращает
    ``BusyLoadingError`` на любые команды, пока загружает данные с диска.
    Healthcheck ``redis-cli ping`` этот момент не ловит.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    attempt = 0
    while True:
        try:
            await client.ping()
            return
        except redis.BusyLoadingError:
            attempt += 1
            if asyncio.get_event_loop().time() >= deadline:
                raise
            log.info("redis_loading_dataset", attempt=attempt)
            await asyncio.sleep(interval)
