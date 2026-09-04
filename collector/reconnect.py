"""Exponential backoff для переподключения WebSocket (требование C-005).

Базовые задержки: 1s → 5s → 15s → 30s → max 60s.
Поверх каждой задержки накладывается случайный jitter ±20%, чтобы
несколько параллельных тасков на одной бирже не реконнектились
синхронно (иначе binance/kucoin/bingx возвращают
``Too many connections``).
"""
from __future__ import annotations

import random

# Первый шаг — 1 секунда: после rate-limit'а бирже нужно дать выдохнуть,
# 100 ms (как было раньше) приводят к моментальному повторному отбою.
BACKOFF_DELAYS: list[float] = [1.0, 5.0, 15.0, 30.0, 60.0]
JITTER = 0.2  # ±20%


def backoff_delay(attempt: int) -> float:
    """Задержка перед попыткой ``attempt`` (0-based) с равномерным jitter ±20%.

    Дальше длины ``BACKOFF_DELAYS`` — фиксируется на максимуме (60s).
    """
    if attempt < 0:
        attempt = 0
    base = BACKOFF_DELAYS[min(attempt, len(BACKOFF_DELAYS) - 1)]
    return base * random.uniform(1.0 - JITTER, 1.0 + JITTER)
