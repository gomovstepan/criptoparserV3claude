"""Unit-тесты расчёта P&L executor'а (Фаза 15).

Запускать ВНУТРИ контейнера executor (там доступен модуль `pnl`):
    docker cp tests/test_pnl_calculator.py arb-executor:/app/
    docker exec arb-executor python -m unittest test_pnl_calculator -v

Модуль `pnl` — чистый stdlib, без внешних зависимостей.
"""
import unittest

from pnl import calculate_pnl


class TestPnLCalculator(unittest.TestCase):
    def test_positive_trade_no_slippage(self):
        r = calculate_pnl(
            buy_price=100.0, sell_price=102.0, amount=1.0,
            buy_fee_pct=0.1, sell_fee_pct=0.1, withdrawal_fee=1.0, slippage_pct=0.0,
        )
        self.assertAlmostEqual(r.gross_pnl, 2.0, places=6)
        # net = 102 - 100 - 0.1 - 0.102 - 1.0 = 0.798
        self.assertAlmostEqual(r.net_pnl, 0.798, places=6)
        self.assertEqual(r.slippage_cost, 0.0)

    def test_slippage_reduces_net_but_not_gross(self):
        base = calculate_pnl(100.0, 102.0, 1.0, 0.1, 0.1, 1.0, 0.0)
        slip = calculate_pnl(100.0, 102.0, 1.0, 0.1, 0.1, 1.0, 0.5)
        # gross считается по «идеальным» ценам — slippage его не меняет
        self.assertEqual(slip.gross_pnl, base.gross_pnl)
        # net проседает из-за худших цен исполнения
        self.assertLess(slip.net_pnl, base.net_pnl)
        self.assertAlmostEqual(slip.net_pnl, -0.21199, places=4)
        self.assertGreater(slip.slippage_cost, 0.0)

    def test_effective_prices_worse_with_slippage(self):
        r = calculate_pnl(100.0, 102.0, 1.0, 0.0, 0.0, 0.0, 0.5)
        self.assertGreater(r.effective_buy, 100.0)   # покупаем дороже
        self.assertLess(r.effective_sell, 102.0)     # продаём дешевле

    def test_negative_spread_is_loss(self):
        r = calculate_pnl(102.0, 100.0, 1.0, 0.1, 0.1, 0.0, 0.0)
        self.assertAlmostEqual(r.gross_pnl, -2.0, places=6)
        self.assertLess(r.net_pnl, 0.0)


if __name__ == "__main__":
    unittest.main()
