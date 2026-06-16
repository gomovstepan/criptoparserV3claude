"""Exponential backoff для переподключения WebSocket (требование C-005).

Задержки: 100ms → 1s → 5s → 30s → max 60s.
"""
from __future__ import annotations

BACKOFF_DELAYS: list[float] = [0.1, 1.0, 5.0, 30.0, 60.0]


def backoff_delay(attempt: int) -> float:
    """Задержка перед попыткой ``attempt`` (0-based). Дальше — максимум 60s."""
    if attempt < 0:
        attempt = 0
    return BACKOFF_DELAYS[min(attempt, len(BACKOFF_DELAYS) - 1)]
