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

    @staticmethod
    def _key(opp: Opportunity) -> str:
        return f"dedup:opp:{opp.symbol}:{opp.buy_exchange}:{opp.sell_exchange}"

    async def is_new(self, opp: Opportunity) -> bool:
        """True, если возможность новая (за последние ttl секунд не было такой же).

        Атомарный check-and-mark. В scan-цикле НЕ используется: там проверка
        (``seen``) и отметка (``mark``) разнесены, чтобы упавшая публикация не
        глушила возможность на весь ttl. Оставлен для одношаговых сценариев.
        """
        created = await self._redis.set(self._key(opp), "1", nx=True, ex=self._ttl)
        return created is True

    async def seen(self, opp: Opportunity) -> bool:
        """True, если такая возможность уже публиковалась за последние ttl секунд."""
        return bool(await self._redis.exists(self._key(opp)))

    async def mark(self, opp: Opportunity) -> None:
        """Отметить возможность как опубликованную (вызывать ПОСЛЕ publish)."""
        await self._redis.set(self._key(opp), "1", ex=self._ttl)
