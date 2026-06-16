"""Фабрика CCXT Pro инстансов бирж.

``create_exchange`` возвращает websocket-клиент CCXT Pro для биржи по её
системному имени (binance, bybit, ...). Rate limiting включён всегда.
"""
from __future__ import annotations

import ccxt.pro as ccxtpro  # CCXT Pro (websocket) поставляется внутри пакета ccxt

from shared.config import EXCHANGES


def create_exchange(name: str):
    """Создать CCXT Pro инстанс биржи. KeyError, если биржа неизвестна."""
    cfg = EXCHANGES[name]
    klass = getattr(ccxtpro, cfg.ccxt_id)
    return klass({
        "enableRateLimit": True,      # соблюдение лимитов биржи (требование C-009)
        "options": {
            # MVP — только spot-рынок (ТЗ, ограничение №1)
            "defaultType": "spot",
            # Не падать на рассинхроне checksum стакана (актуально для bitget):
            # CCXT Pro иначе бросает исключение и рвёт подписку.
            "watchOrderBook": {"checksum": False},
        },
    })
