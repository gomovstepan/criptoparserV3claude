"""Интеграционный тест потока данных: prices → Redis → scanner → opportunities (Фаза 15).

Имитирует тики collector'а (XADD в stream `prices`) и проверяет, что живой
scanner находит спред и публикует opportunity в stream `opportunities`.

Запускать ВНУТРИ контейнера api-gateway (есть и `redis`, и сеть до arb-redis):
    docker cp tests/test_integration.py arb-api-gateway:/app/
    docker exec arb-api-gateway python -m unittest test_integration -v

Требует поднятых redis + scanner.
"""
import os
import time
import unittest

import redis

R = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    password=os.environ.get("REDIS_PASSWORD") or None,
    decode_responses=True,
)
SYMBOL = "ZZZ/USDT"  # синтетическая пара, которой нет в реальном потоке — изолирует тест


class TestCollectorToScanner(unittest.TestCase):
    def test_injected_prices_produce_opportunity(self):
        # сбрасываем возможный dedup-ключ, чтобы opportunity точно опубликовалась
        R.delete(f"dedup:opp:{SYMBOL}:binance:kucoin")

        # два тика с явным спредом: buy binance(ask=100) → sell kucoin(bid=103) = 3%
        R.xadd("prices", {"exchange": "binance", "symbol": SYMBOL, "bid": "100", "ask": "100"})
        R.xadd("prices", {"exchange": "kucoin", "symbol": SYMBOL, "bid": "103", "ask": "103"})

        # ждём, пока scanner обработает и опубликует opportunity
        found = None
        deadline = time.time() + 10
        while time.time() < deadline and found is None:
            for _id, f in R.xrevrange("opportunities", count=100):
                if f.get("symbol") == SYMBOL:
                    found = f
                    break
            if found is None:
                time.sleep(0.5)

        self.assertIsNotNone(found, "scanner не опубликовал opportunity по инжектированным ценам")
        self.assertEqual(found["buy_exchange"], "binance")
        self.assertEqual(found["sell_exchange"], "kucoin")
        self.assertGreaterEqual(float(found["gross_spread_pct"]), 0.3)


if __name__ == "__main__":
    unittest.main()
