"""Проверка доступности биржи через публичный REST API (CCXT, без ключей).

Используется на фазе 2 для smoke-теста подключения к биржам.
"""
from __future__ import annotations

import ccxt

from shared.config import EXCHANGES


def test_exchange_connection(exchange_id: str, symbol: str = "BTC/USDT") -> dict:
    """Запросить публичный ticker и вернуть bid/ask.

    Пример:
        >>> test_exchange_connection("binance")
        {'exchange': 'binance', 'symbol': 'BTC/USDT', 'bid': 67432.15, 'ask': 67433.8}
    """
    cfg = EXCHANGES[exchange_id]
    klass = getattr(ccxt, cfg.ccxt_id)
    exchange = klass({"enableRateLimit": True})
    ticker = exchange.fetch_ticker(symbol)
    return {
        "exchange": exchange_id,
        "symbol": symbol,
        "bid": ticker["bid"],
        "ask": ticker["ask"],
    }


if __name__ == "__main__":  # ручной запуск внутри контейнера: python exchanges.py binance
    import sys

    ex = sys.argv[1] if len(sys.argv) > 1 else "binance"
    print(test_exchange_connection(ex))
