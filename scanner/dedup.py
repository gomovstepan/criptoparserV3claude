"""Дедупликация opportunities через Redis (требование S-006).

Одна и та же возможность (symbol + buy_exchange + sell_exchange) не публикуется
повторно в течение ``ttl`` секунд. Реализовано атомарным ``SET key NX EX ttl``.
"""
from __future__ import annotations

import redis.asyncio as redis

from shared.models import Opportunity


class OpportunityDedup:
    def __init__(self, redis_client: redis.Redis, ttl: int = 5) -> None:
        self._redis = redis_client
        self._ttl = ttl

    async def is_new(self, opp: Opportunity) -> bool:
        """True, если возможность новая (за последние ttl секунд не было такой же)."""
        key = f"dedup:opp:{opp.symbol}:{opp.buy_exchange}:{opp.sell_exchange}"
        created = await self._redis.set(key, "1", nx=True, ex=self._ttl)
        return created is True
