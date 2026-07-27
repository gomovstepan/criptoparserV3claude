"""Публикация тиков цен в Redis Stream ``prices`` (XADD).

Stream ограничен по длине (~100k записей, approximate trim) — это backpressure,
примерно 10 секунд данных при пиковой нагрузке.
"""
from __future__ import annotations

import redis.asyncio as redis

from shared.config import settings
from shared.depth import DEPTH_TTL_SEC, depth_key, dump_depth
from shared.models import PriceTick
from shared.redis_utils import wait_until_ready

PRICES_STREAM = "prices"
PRICES_MAXLEN = 100_000


class RedisPublisher:
    """Тонкая обёртка над redis-py для публикации цен."""

    def __init__(self) -> None:
        self._redis: redis.Redis | None = None

    async def connect(self) -> None:
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        await wait_until_ready(self._redis)

    async def publish_price(self, tick: PriceTick) -> None:
        """XADD одного тика в stream ``prices``."""
        assert self._redis is not None, "RedisPublisher не подключён"
        await self._redis.xadd(
            PRICES_STREAM,
            tick.to_redis(),
            maxlen=PRICES_MAXLEN,
            approximate=True,
        )

    async def publish_depth(
        self, exchange: str, symbol: str, bids: list, asks: list, ts: int,
    ) -> None:
        """SET depth:{exchange}:{symbol} = JSON топ-N уровней с TTL."""
        assert self._redis is not None, "RedisPublisher не подключён"
        await self._redis.set(
            depth_key(exchange, symbol),
            dump_depth(bids, asks, ts),
            ex=DEPTH_TTL_SEC,
        )

    async def delete_depth(self, exchange: str, symbols: list[str]) -> None:
        """Удалить depth-ключи биржи (при вотчдог-реконнекте).

        Scanner/executor мгновенно видят отсутствие книги вместо того, чтобы
        дожидаться истечения TTL по заведомо мёртвым данным.
        """
        assert self._redis is not None, "RedisPublisher не подключён"
        if symbols:
            await self._redis.delete(*[depth_key(exchange, s) for s in symbols])

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
