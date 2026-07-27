"""Unit-тесты формулы P&L executor'а (`executor/pnl.py::settle_trade`).

Это ТА ЖЕ функция, которую вызывает боевой движок `paper_trading.py` —
раньше тут проверялась устаревшая процентная модель slippage, которую
в продакшене не вызывал никто.

Запускать ВНУТРИ контейнера executor (там доступен модуль `pnl`):
    docker cp tests/test_pnl_calculator.py arb-executor:/app/
    docker exec arb-executor python -m unittest test_pnl_calculator -v

Модуль `pnl` — чистый stdlib, без внешних зависимостей.
"""
import unittest

from pnl import settle_trade


class TestSettleTrade(unittest.TestCase):
    def test_no_slippage_when_vwap_equals_top_of_book(self):
        """Весь объём влез в лучшую цену: издержки — только комиссии."""
        r = settle_trade(
            amount=1.0,
            effective_buy=100.0, effective_sell=102.0,
            top_ask=100.0, top_bid=102.0,
            buy_fee_pct=0.1, sell_fee_pct=0.1,
        )
        self.assertAlmostEqual(r.gross_pnl, 2.0, places=6)
        self.assertAlmostEqual(r.slippage_cost, 0.0, places=9)
        # net = 102 - 100 - 0.1 - 0.102 = 1.798
        self.assertAlmostEqual(r.net_pnl, 1.798, places=6)

    def test_walking_the_book_costs_slippage(self):
        """VWAP хуже top-of-book по обеим ногам — net проседает, gross нет."""
        flat = settle_trade(1.0, 100.0, 102.0, 100.0, 102.0, 0.1, 0.1)
        walked = settle_trade(1.0, 100.5, 101.5, 100.0, 102.0, 0.1, 0.1)
        # gross считается по top-of-book, его глубина стакана не меняет
        self.assertAlmostEqual(walked.gross_pnl, flat.gross_pnl, places=6)
        self.assertLess(walked.net_pnl, flat.net_pnl)
        # проскальзывание = 0.5 (покупка) + 0.5 (продажа) на единицу объёма
        self.assertAlmostEqual(walked.slippage_cost, 1.0, places=6)

    def test_identity_net_equals_gross_minus_costs(self):
        """Ключевой инвариант: net == gross - slippage - обе комиссии."""
        r = settle_trade(2.5, 100.4, 101.6, 100.0, 102.0, 0.2, 0.3)
        self.assertAlmostEqual(
            r.net_pnl,
            r.gross_pnl - r.slippage_cost - r.buy_fee - r.sell_fee,
            places=6,
        )

    def test_slippage_is_never_negative(self):
        """Проход по стакану может только ухудшить цену, но не улучшить."""
        r = settle_trade(3.0, 100.9, 101.1, 100.0, 102.0, 0.1, 0.1)
        self.assertGreaterEqual(r.slippage_cost, 0.0)

    def test_withdrawal_fee_is_not_part_of_net_pnl(self):
        """Комиссия вывода списывается при ребалансе, а не за сделку.

        Поэтому в результате её вообще нет — ни поля, ни слагаемого.
        """
        r = settle_trade(1.0, 100.0, 102.0, 100.0, 102.0, 0.0, 0.0)
        self.assertFalse(hasattr(r, "withdrawal_fee"))
        self.assertAlmostEqual(r.net_pnl, 2.0, places=6)

    def test_negative_spread_is_loss(self):
        r = settle_trade(1.0, 102.0, 100.0, 102.0, 100.0, 0.1, 0.1)
        self.assertAlmostEqual(r.gross_pnl, -2.0, places=6)
        self.assertLess(r.net_pnl, 0.0)

    def test_fees_scale_with_notional(self):
        small = settle_trade(1.0, 100.0, 102.0, 100.0, 102.0, 0.1, 0.1)
        big = settle_trade(10.0, 100.0, 102.0, 100.0, 102.0, 0.1, 0.1)
        self.assertAlmostEqual(big.buy_fee, small.buy_fee * 10, places=6)
        self.assertAlmostEqual(big.sell_fee, small.sell_fee * 10, places=6)


if __name__ == "__main__":
    unittest.main()
