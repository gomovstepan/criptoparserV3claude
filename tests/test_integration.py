"""Интеграционный тест потока данных: prices → Redis → scanner → opportunities (Фаза 15).

Имитирует тики collector'а (XADD в stream `prices` + depth-ключи) и проверяет,
что живой scanner находит спред и публикует opportunity в stream `opportunities`.
Глубина обязательна: fallback на top-of-book удалён, без свежих книг обеих бирж
сканер пару не публикует — тест воспроизводит полный контракт collector'а.

Запускать ВНУТРИ контейнера api-gateway (есть и `redis`, и сеть до arb-redis):
    docker cp tests/test_integration.py arb-api-gateway:/app/
    docker exec arb-api-gateway python -m unittest test_integration -v

Требует поднятых redis + scanner.
"""
import json
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
    def setUp(self):
        # Взводим kill switch на время теста: инжектированный 3%-спред с живой
        # глубиной ИСПОЛНИМ, и настоящий executor радостно запишет фантомную
        # сделку в trades/balance (однажды так и случилось: +22.65 «прибыли»).
        # Сканер kill switch не читает — публикация opportunity не страдает.
        self._prev_kill = R.get("executor:kill_switch")
        R.set("executor:kill_switch", "1")

    def tearDown(self):
        # Прежде чем вернуть kill switch, дождаться, пока executor ВЫЧИТАЕТ
        # инжектированную возможность: восстановление «0» до consumption
        # позволило бы ему исполнить фантом (kill switch читается per-message).
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                groups = R.xinfo_groups("opportunities")
                lag = next(
                    (g.get("lag") for g in groups if g.get("name") == "executor-cg"), 0,
                )
                if not lag:
                    break
            except redis.ResponseError:
                break
            time.sleep(0.2)
        if self._prev_kill is None:
            R.set("executor:kill_switch", "0")
        else:
            R.set("executor:kill_switch", self._prev_kill)

    def test_injected_prices_produce_opportunity(self):
        # сбрасываем возможный dedup-ключ, чтобы opportunity точно опубликовалась
        R.delete(f"dedup:opp:{SYMBOL}:binance:kucoin")

        # Глубина обеих бирж (как её пишет collector): с запасом на notional
        # $1000, чтобы VWAP совпал с top-ценой.
        now_ms = int(time.time() * 1000)
        R.set(f"depth:binance:{SYMBOL}", json.dumps(
            {"ts": now_ms, "bids": [[100.0, 1000.0]], "asks": [[100.0, 1000.0]]}), ex=5)
        R.set(f"depth:kucoin:{SYMBOL}", json.dumps(
            {"ts": now_ms, "bids": [[103.0, 1000.0]], "asks": [[103.0, 1000.0]]}), ex=5)

        # два тика с явным спредом: buy binance(ask=100) → sell kucoin(bid=103) = 3%
        R.xadd("prices", {"exchange": "binance", "symbol": SYMBOL, "bid": "100", "ask": "100",
                          "received_at": str(now_ms)})
        R.xadd("prices", {"exchange": "kucoin", "symbol": SYMBOL, "bid": "103", "ask": "103",
                          "received_at": str(now_ms)})

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
