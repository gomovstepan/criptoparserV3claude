"""Простой in-memory rate limiter со скользящим окном (Фаза 9).

REST: 100 запросов/мин на IP (требование G-006).
"""
from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_requests: int = 100, window_sec: int = 60) -> None:
        self.max_requests = max_requests
        self.window_sec = window_sec
        self._hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str) -> bool:
        """True — запрос разрешён; False — лимит превышен."""
        now = time.time()
        hits = self._hits[key]
        while hits and hits[0] < now - self.window_sec:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True


rest_limiter = RateLimiter(max_requests=100, window_sec=60)
