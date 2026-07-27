"""Unit-тесты расчёта спредов scanner'а (Фаза 15 + гейты сейфти).

Запускать ВНУТРИ контейнера scanner (там доступны `spread_calculator` и `shared`):
    docker cp tests/test_spread_calculator.py arb-scanner:/app/
    docker exec arb-scanner python -m unittest test_spread_calculator -v

Зависимостей сверх рантайма scanner'а не требует (чистая функция).

ВАЖНО: fallback на top-of-book удалён — цены считаются ТОЛЬКО по глубине,
поэтому каждый кейс обязан передавать книги обеих бирж (см. _deep_book).
"""
import unittest

from spread_calculator import calculate_spreads


def _deep_book(bid: float, ask: float, qty: float = 1000.0) -> dict:
    """Книга с запасом: VWAP на любой тестовый notional равен top-цене."""
    return {"ts": 0, "bids": [[bid, qty]], "asks": [[ask, qty]]}


class TestSpreadCalculator(unittest.TestCase):
    def _prices(self):
        # binance дешевле, kucoin дороже → арбитраж binance→kucoin
        return {
            "binance": {"bid": 100.0, "ask": 100.0},
            "kucoin": {"bid": 102.0, "ask": 102.0},
        }

    def _depth(self):
        return {
            "binance": _deep_book(100.0, 100.0),
            "kucoin": _deep_book(102.0, 102.0),
        }

    def test_gross_and_net_spread(self):
        opps = calculate_spreads(
            "BTC/USDT", self._prices(), min_spread_pct=1.0, depth=self._depth(),
        )
        # только binance(buy по ask=100) → kucoin(sell по bid=102); обратное направление отрицательно
        self.assertEqual(len(opps), 1)
        o = opps[0]
        self.assertEqual(o.buy_exchange, "binance")
        self.assertEqual(o.sell_exchange, "kucoin")
        self.assertEqual(o.buy_price, 100.0)
        self.assertEqual(o.sell_price, 102.0)
        self.assertAlmostEqual(o.gross_spread_pct, 2.0, places=4)
        # net = gross - taker(binance 0.1) - taker(kucoin 0.1)
        #       - withdrawal(kucoin 1.5 USDT / notional 1000 * 100 = 0.15) = 1.65
        self.assertAlmostEqual(o.net_spread_pct, 1.65, places=4)

    def test_min_spread_filters_out(self):
        opps = calculate_spreads(
            "BTC/USDT", self._prices(), min_spread_pct=5.0, depth=self._depth(),
        )
        self.assertEqual(opps, [])

    def test_min_net_spread_filters_out(self):
        """Гросс проходит, но за вычетом комиссий обеих ног (0.2%) спред мал."""
        prices = {
            "binance": {"bid": 100.0, "ask": 100.0},
            "kucoin": {"bid": 100.5, "ask": 100.5},   # gross 0.5%
        }
        depth = {
            "binance": _deep_book(100.0, 100.0),
            "kucoin": _deep_book(100.5, 100.5),
        }
        # net_fees = 0.5 - 0.1 - 0.1 = 0.3
        filtered = calculate_spreads(
            "BTC/USDT", prices, min_spread_pct=0.1, depth=depth,
            min_net_spread_pct=0.4,
        )
        self.assertEqual(filtered, [])
        passed = calculate_spreads(
            "BTC/USDT", prices, min_spread_pct=0.1, depth=depth,
            min_net_spread_pct=0.25,
        )
        self.assertEqual(len(passed), 1)

    def test_no_depth_means_no_opportunity(self):
        """Fallback на top-of-book удалён: без свежей глубины пары нет.

        Раньше именно этот путь публиковал фантомные спреды от dust-ордеров
        (все убыточные сделки в истории системы) — теперь он закрыт.
        """
        # глубины нет вовсе
        self.assertEqual(
            calculate_spreads("BTC/USDT", self._prices(), min_spread_pct=0.1), [],
        )
        # глубина есть только с одной стороны
        one_sided = {"binance": _deep_book(100.0, 100.0)}
        self.assertEqual(
            calculate_spreads(
                "BTC/USDT", self._prices(), min_spread_pct=0.1, depth=one_sided,
            ),
            [],
        )

    def test_withdrawal_fee_reduces_net(self):
        # sell на bybit (withdrawal_usdt=1.0) — net должен просесть
        prices = {
            "binance": {"bid": 100.0, "ask": 100.0},
            "bybit": {"bid": 102.0, "ask": 102.0},
        }
        depth = {
            "binance": _deep_book(100.0, 100.0),
            "bybit": _deep_book(102.0, 102.0),
        }
        # notional=100 USD → withdrawal_pct = 1.0/100*100 = 1.0%
        opps = calculate_spreads(
            "BTC/USDT", prices, min_spread_pct=0.1,
            estimated_notional_usd=100.0, depth=depth,
        )
        o = next(o for o in opps if o.sell_exchange == "bybit")
        self.assertAlmostEqual(o.gross_spread_pct, 2.0, places=4)
        # net = 2.0 - 0.1 - 0.1 - 1.0 = 0.8
        self.assertAlmostEqual(o.net_spread_pct, 0.8, places=4)

    def test_unknown_exchange_ignored(self):
        prices = {
            "binance": {"bid": 100.0, "ask": 100.0},
            "notreal": {"bid": 200.0, "ask": 200.0},
        }
        depth = {
            "binance": _deep_book(100.0, 100.0),
            "notreal": _deep_book(200.0, 200.0),
        }
        opps = calculate_spreads("BTC/USDT", prices, min_spread_pct=0.1, depth=depth)
        # 'notreal' не в EXCHANGES → остаётся одна биржа → пар нет
        self.assertEqual(opps, [])

    def test_depth_prunes_phantom_spread(self):
        # top-of-book даёт 2% спред, но глубины на $1000 недостаточно
        prices = {
            "binance": {"bid": 100.0, "ask": 100.0},
            "kucoin":  {"bid": 102.0, "ask": 102.0},
        }
        depth = {
            "binance": {"ts": 0, "bids": [[100.0, 10.0]], "asks": [[100.0, 1.0]]},
            "kucoin":  {"ts": 0, "bids": [[102.0, 10.0]], "asks": [[102.0, 10.0]]},
        }
        opps = calculate_spreads(
            "BTC/USDT", prices, min_spread_pct=1.0,
            estimated_notional_usd=1000.0, depth=depth,
        )
        self.assertEqual(opps, [])

    def test_depth_produces_vwap_prices(self):
        prices = {
            "binance": {"bid": 100.0, "ask": 100.0},
            "kucoin":  {"bid": 102.0, "ask": 102.0},
        }
        # Глубины хватает, но часть объёма исполняется по худшим уровням:
        # binance asks: 8@100 + 100@101; kucoin bids: 8@102 + 100@101.5
        # $1000: 8@100=$800, 200/101≈1.980 base → amount≈9.980, vwap_buy≈100.198
        # sell 9.980: 8@102 + 1.980@101.5 → vwap_sell≈101.90 → gross≈1.7% < 2%
        depth = {
            "binance": {"ts": 0, "bids": [[100.0, 100.0]],
                         "asks": [[100.0, 8.0], [101.0, 100.0]]},
            "kucoin":  {"ts": 0, "bids": [[102.0, 8.0], [101.5, 100.0]],
                         "asks": [[102.0, 100.0]]},
        }
        opps = calculate_spreads(
            "BTC/USDT", prices, min_spread_pct=0.0,
            estimated_notional_usd=1000.0, depth=depth,
        )
        buy = next(o for o in opps if o.buy_exchange == "binance" and o.sell_exchange == "kucoin")
        self.assertGreater(buy.buy_price, 100.0)
        self.assertLess(buy.sell_price, 102.0)
        self.assertLess(buy.gross_spread_pct, 2.0)
        self.assertGreater(buy.gross_spread_pct, 1.0)


if __name__ == "__main__":
    unittest.main()
