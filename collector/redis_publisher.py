"""Публикация тиков цен в Redis Stream ``prices`` (XADD).

Stream ограничен по длине (~100k записей, approximate trim) — это backpressure,
примерно 10 секунд данных при пиковой нагрузке.
"""
from __future__ import annotations

import redis.asyncio as redis

from shared.config import settings
from shared.models import PriceTick

PRICES_STREAM = "prices"
PRICES_MAXLEN = 100_000


class RedisPublisher:
    """Тонкая обёртка над redis-py для публикации цен."""

    def __init__(self) -> None:
        self._redis: redis.Redis | None = None

    async def connect(self) -> None:
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        await self._redis.ping()

    async def publish_price(self, tick: PriceTick) -> None:
        """XADD одного тика в stream ``prices``."""
        assert self._redis is not None, "RedisPublisher не подключён"
        await self._redis.xadd(
            PRICES_STREAM,
            tick.to_redis(),
            maxlen=PRICES_MAXLEN,
            approximate=True,
        )

    async def ping(self) -> bool:
        if self._redis is None:
            return False
        try:
            return bool(await self._redis.ping())
        except redis.RedisError:
            return False

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
