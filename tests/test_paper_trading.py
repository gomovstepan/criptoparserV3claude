"""Тесты движка paper-trading (`executor/paper_trading.py::execute_opportunity`).

Раньше эта логика не была покрыта ничем: единственный тест executor'а проверял
функцию, которую продакшн не вызывал, а `test_integration.py` доходит только до
стрима `opportunities` и до исполнения сделки не добирается.

Проверяются условия отказа (kill switch, нехватка баланса, устаревшая глубина,
тонкий стакан) и happy path с точными дельтами балансов.

Запускать ВНУТРИ контейнера executor (нужны модули `paper_trading`, `balance`,
`rebalance`, `pnl` и пакет `shared`):
    docker cp tests/test_paper_trading.py arb-executor:/app/
    docker exec arb-executor python -m unittest test_paper_trading -v

Redis подменён заглушкой — только stdlib `unittest` + `asyncio`, сеть не нужна.
"""
import asyncio
import json
import time
import unittest

from paper_trading import MIN_NOTIONAL_USDT, PaperTradingEngine
from rebalance import KILL_SWITCH_KEY
from shared.depth import depth_key
from shared.models import Opportunity

BUY_EX = "binance"
SELL_EX = "bybit"
DONOR_EX = "kucoin"
SYMBOL = "BTC/USDT"


class FakeRedis:
    """Минимальная заглушка: только вызовы, которые делает движок и его хелперы."""

    def __init__(self, balances=None, kv=None):
        self.hashes = {
            f"balance:{ex}": {"USDT": repr(float(v))}
            for ex, v in (balances or {}).items()
        }
        self.kv = dict(kv or {})

    async def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    async def hincrbyfloat(self, key, field, delta):
        current = float(self.hashes.setdefault(key, {}).get(field, 0.0))
        new = current + float(delta)
        self.hashes[key][field] = repr(new)
        return new

    async def get(self, key):
        return self.kv.get(key)

    async def set(self, key, value, **_kwargs):
        self.kv[key] = value
        return True

    async def mget(self, keys):
        return [self.kv.get(k) for k in keys]

    # ── помощники теста ──
    def balance(self, exchange):
        return float(self.hashes.get(f"balance:{exchange}", {}).get("USDT", 0.0))

    def put_depth(self, exchange, symbol, bids, asks, age_ms=0):
        ts = int(time.time() * 1000) - age_ms
        self.kv[depth_key(exchange, symbol)] = json.dumps(
            {"ts": ts, "bids": bids, "asks": asks}
        )


def make_opportunity(buy_fee_pct=0.1, sell_fee_pct=0.1, detected_at=None):
    return Opportunity(
        id="opp_test_1",
        symbol=SYMBOL,
        buy_exchange=BUY_EX,
        sell_exchange=SELL_EX,
        buy_price=100.0,
        sell_price=102.0,
        gross_spread_pct=2.0,
        buy_fee_pct=buy_fee_pct,
        sell_fee_pct=sell_fee_pct,
        net_spread_pct=1.8,
        detected_at=detected_at if detected_at is not None else int(time.time() * 1000),
    )


def run(coro):
    return asyncio.run(coro)


class TestExecuteOpportunity(unittest.TestCase):
    def _engine_with_book(self, balances=None, **kwargs):
        r = FakeRedis(balances or {BUY_EX: 10_000.0, SELL_EX: 10_000.0})
        # Стакан с запасом: 50 единиц по лучшей цене покрывают любой notional теста
        r.put_depth(BUY_EX, SYMBOL, bids=[[99.0, 50.0]], asks=[[100.0, 50.0]])
        r.put_depth(SELL_EX, SYMBOL, bids=[[102.0, 50.0]], asks=[[103.0, 50.0]])
        return r, PaperTradingEngine(r, **kwargs)

    def test_kill_switch_blocks_execution(self):
        r, engine = self._engine_with_book()
        engine.kill_switch = True
        self.assertIsNone(run(engine.execute_opportunity(make_opportunity())))
        # балансы не тронуты
        self.assertEqual(r.balance(BUY_EX), 10_000.0)

    def test_skipped_when_balance_at_threshold_and_no_donor(self):
        """Ребаланс невозможен → сделки нет и взводится kill switch."""
        r = FakeRedis({BUY_EX: 50.0})
        r.put_depth(BUY_EX, SYMBOL, bids=[[99.0, 50.0]], asks=[[100.0, 50.0]])
        r.put_depth(SELL_EX, SYMBOL, bids=[[102.0, 50.0]], asks=[[103.0, 50.0]])
        engine = PaperTradingEngine(r, rebalance_threshold=100.0)
        self.assertIsNone(run(engine.execute_opportunity(make_opportunity())))
        self.assertEqual(r.kv.get(KILL_SWITCH_KEY), "1")

    def test_rebalance_tops_up_and_is_reported(self):
        r = FakeRedis({BUY_EX: 50.0, SELL_EX: 10_000.0, DONOR_EX: 20_000.0})
        r.put_depth(BUY_EX, SYMBOL, bids=[[99.0, 500.0]], asks=[[100.0, 500.0]])
        r.put_depth(SELL_EX, SYMBOL, bids=[[102.0, 500.0]], asks=[[103.0, 500.0]])
        engine = PaperTradingEngine(r, rebalance_threshold=100.0)
        res = run(engine.execute_opportunity(make_opportunity()))
        self.assertIsNotNone(res)
        self.assertIsNotNone(res.rebalance)
        self.assertEqual(res.rebalance.donor, DONOR_EX)
        # донор отдал половину, kill switch не взводился
        self.assertAlmostEqual(r.balance(DONOR_EX), 10_000.0, places=6)
        self.assertNotEqual(r.kv.get(KILL_SWITCH_KEY), "1")

    def test_rebalance_denied_when_donor_would_fall_below_threshold(self):
        """Анти-пинг-понг: донор, который после отдачи половины сам уйдёт
        под порог, не годится — иначе следующая сделка через него запустила бы
        обратный перевод с уплатой комиссии за каждый круг."""
        r = FakeRedis({BUY_EX: 50.0, DONOR_EX: 150.0})
        r.put_depth(BUY_EX, SYMBOL, bids=[[99.0, 50.0]], asks=[[100.0, 50.0]])
        r.put_depth(SELL_EX, SYMBOL, bids=[[102.0, 50.0]], asks=[[103.0, 50.0]])
        engine = PaperTradingEngine(r, rebalance_threshold=100.0)
        # 150/2 = 75 <= 100 → донор не подходит, kill switch, балансы не тронуты
        self.assertIsNone(run(engine.execute_opportunity(make_opportunity())))
        self.assertEqual(r.kv.get(KILL_SWITCH_KEY), "1")
        self.assertAlmostEqual(r.balance(DONOR_EX), 150.0, places=6)
        self.assertAlmostEqual(r.balance(BUY_EX), 50.0, places=6)

    def test_rebalance_persisted_when_trade_skipped(self):
        """Ребаланс случился, но сделка отвалилась (тонкая книга на покупку) —
        результат обязан вернуться с trade=None, чтобы движение ребаланса
        доехало до hypertable, а не потерялось.

        Причина скипа — именно тонкая книга: проверка свежести глубины теперь
        идёт ДО ребаланса (комиссия вывода не жжётся ради мёртвого стакана),
        так что скип по stale-depth ребаланса больше не порождает."""
        r = FakeRedis({BUY_EX: 50.0, SELL_EX: 10_000.0, DONOR_EX: 20_000.0})
        # Свежая, но тонкая книга: после ребаланса notional ~1000 USDT,
        # а на asks всего 0.5 * 100 = 50 USDT.
        r.put_depth(BUY_EX, SYMBOL, [[99.0, 50.0]], [[100.0, 0.5]])
        r.put_depth(SELL_EX, SYMBOL, [[102.0, 500.0]], [[103.0, 500.0]])
        engine = PaperTradingEngine(r, rebalance_threshold=100.0)
        res = run(engine.execute_opportunity(make_opportunity()))
        self.assertIsNotNone(res)
        self.assertIsNone(res.trade)
        self.assertEqual(res.balance_updates, [])
        self.assertIsNotNone(res.rebalance)
        self.assertEqual(res.rebalance.donor, DONOR_EX)
        # Redis уже подвинут: донор отдал половину, получатель получил net
        self.assertAlmostEqual(r.balance(DONOR_EX), 10_000.0, places=6)
        self.assertAlmostEqual(
            r.balance(BUY_EX), 50.0 + res.rebalance.net_amount, places=6
        )

    def test_no_rebalance_when_depth_stale(self):
        """Свежесть глубины проверяется ДО ребаланса: комиссия вывода не
        списывается ради возможности, которую отбраковывает мёртвый стакан."""
        r = FakeRedis({BUY_EX: 50.0, SELL_EX: 10_000.0, DONOR_EX: 20_000.0})
        r.put_depth(BUY_EX, SYMBOL, [[99.0, 50.0]], [[100.0, 50.0]], age_ms=30_000)
        r.put_depth(SELL_EX, SYMBOL, [[102.0, 50.0]], [[103.0, 50.0]], age_ms=30_000)
        engine = PaperTradingEngine(r, rebalance_threshold=100.0)
        self.assertIsNone(run(engine.execute_opportunity(make_opportunity())))
        # балансы не тронуты — ребаланс не запускался
        self.assertAlmostEqual(r.balance(DONOR_EX), 20_000.0, places=6)
        self.assertAlmostEqual(r.balance(BUY_EX), 50.0, places=6)

    def test_skipped_when_notional_below_minimum(self):
        r, engine = self._engine_with_book(
            {BUY_EX: 500.0, SELL_EX: 10_000.0}, max_position_pct=1.0,
        )
        # 1% от 500 = 5 USDT < MIN_NOTIONAL_USDT
        self.assertLess(500.0 * 0.01, MIN_NOTIONAL_USDT)
        self.assertIsNone(run(engine.execute_opportunity(make_opportunity())))
        self.assertEqual(r.balance(BUY_EX), 500.0)

    def test_skipped_when_depth_is_stale(self):
        r = FakeRedis({BUY_EX: 10_000.0, SELL_EX: 10_000.0})
        r.put_depth(BUY_EX, SYMBOL, [[99.0, 50.0]], [[100.0, 50.0]], age_ms=30_000)
        r.put_depth(SELL_EX, SYMBOL, [[102.0, 50.0]], [[103.0, 50.0]], age_ms=30_000)
        engine = PaperTradingEngine(r)
        self.assertIsNone(run(engine.execute_opportunity(make_opportunity())))
        self.assertEqual(r.balance(BUY_EX), 10_000.0)

    def test_skipped_when_depth_missing(self):
        r = FakeRedis({BUY_EX: 10_000.0, SELL_EX: 10_000.0})
        engine = PaperTradingEngine(r)
        self.assertIsNone(run(engine.execute_opportunity(make_opportunity())))

    def test_skipped_when_buy_book_too_thin(self):
        """Стакана не хватает на плановый объём — фантомный спред отбрасывается."""
        r = FakeRedis({BUY_EX: 10_000.0, SELL_EX: 10_000.0})
        r.put_depth(BUY_EX, SYMBOL, [[99.0, 50.0]], [[100.0, 0.5]])   # всего 50 USDT
        r.put_depth(SELL_EX, SYMBOL, [[102.0, 50.0]], [[103.0, 50.0]])
        engine = PaperTradingEngine(r)   # notional = 1000 USDT
        self.assertIsNone(run(engine.execute_opportunity(make_opportunity())))
        self.assertEqual(r.balance(BUY_EX), 10_000.0)

    def test_skipped_when_opportunity_expired(self):
        """Гейт возраста: opportunity старше ttl_seconds не исполняется —
        иначе после простоя executor скупил бы весь бэклог по текущим ценам."""
        r, engine = self._engine_with_book()
        old = make_opportunity(detected_at=int(time.time() * 1000) - 10_000)  # ttl=5с
        self.assertIsNone(run(engine.execute_opportunity(old)))
        self.assertEqual(r.balance(BUY_EX), 10_000.0)

    def test_skipped_when_unprofitable_and_cooldown_set(self):
        """ГЕЙТ ПРИБЫЛЬНОСТИ: dust-ордер на топе → VWAP покупки съедает спред,
        net_pnl < 0 → сделка НЕ исполняется, балансы не тронуты, связка уходит
        в кулдаун. Это ровно сценарий реальных убыточных сделок (LINK/bingx)."""
        r = FakeRedis({BUY_EX: 10_000.0, SELL_EX: 10_000.0})
        # На топе $50 по 100, дальше обрыв до 110: notional 1000 → VWAP ≈ 109.4
        r.put_depth(BUY_EX, SYMBOL, [[99.0, 500.0]], [[100.0, 0.5], [110.0, 500.0]])
        r.put_depth(SELL_EX, SYMBOL, [[102.0, 500.0]], [[103.0, 500.0]])
        engine = PaperTradingEngine(r)
        self.assertIsNone(run(engine.execute_opportunity(make_opportunity())))
        self.assertEqual(r.balance(BUY_EX), 10_000.0)
        self.assertEqual(r.balance(SELL_EX), 10_000.0)
        self.assertIn(f"cooldown:{SYMBOL}:{BUY_EX}:{SELL_EX}", r.kv)

    def test_skipped_when_cooldown_active(self):
        """Активный кулдаун глушит связку до истечения TTL."""
        r, engine = self._engine_with_book()
        r.kv[f"cooldown:{SYMBOL}:{BUY_EX}:{SELL_EX}"] = "1"
        self.assertIsNone(run(engine.execute_opportunity(make_opportunity())))
        self.assertEqual(r.balance(BUY_EX), 10_000.0)

    def test_min_profit_threshold_blocks_marginal_trade(self):
        """Настраиваемый порог: сделка с net 17.98 < min_profit_usd=100 не идёт."""
        r, engine = self._engine_with_book(min_profit_usd=100.0)
        self.assertIsNone(run(engine.execute_opportunity(make_opportunity())))
        self.assertEqual(r.balance(BUY_EX), 10_000.0)

    def test_happy_path_balances_and_pnl(self):
        r, engine = self._engine_with_book()
        res = run(engine.execute_opportunity(make_opportunity()))
        self.assertIsNotNone(res)
        trade = res.trade

        # notional = 10% от 10 000 = 1000 USDT по 100 → 10 единиц базового актива
        self.assertAlmostEqual(trade.amount, 10.0, places=6)
        self.assertAlmostEqual(trade.buy_price, 100.0, places=6)
        self.assertAlmostEqual(trade.sell_price, 102.0, places=6)
        self.assertAlmostEqual(trade.buy_fee, 1.0, places=6)      # 1000 * 0.1%
        self.assertAlmostEqual(trade.sell_fee, 1.02, places=6)    # 1020 * 0.1%
        self.assertAlmostEqual(trade.gross_pnl, 20.0, places=6)
        self.assertAlmostEqual(trade.net_pnl, 17.98, places=6)
        self.assertEqual(trade.status, "completed")
        # комиссия вывода не входит в сделку — она списывается при ребалансе
        self.assertEqual(trade.withdrawal_fee, 0.0)
        # top-of-book обеих ног сохраняется для сверки gross/slippage постфактум
        self.assertAlmostEqual(trade.buy_top_ask, 100.0, places=6)
        self.assertAlmostEqual(trade.sell_top_bid, 102.0, places=6)

        # балансы: buy -= (1000 + 1), sell += (1020 - 1.02)
        self.assertAlmostEqual(r.balance(BUY_EX), 8_999.0, places=6)
        self.assertAlmostEqual(r.balance(SELL_EX), 11_018.98, places=6)

    def test_balance_updates_match_trade(self):
        """Дельты, уходящие в hypertable, совпадают с фактическим Redis."""
        r, engine = self._engine_with_book()
        res = run(engine.execute_opportunity(make_opportunity()))
        updates = {ex: (new, change) for ex, new, change in res.balance_updates}
        self.assertAlmostEqual(updates[BUY_EX][0], r.balance(BUY_EX), places=6)
        self.assertAlmostEqual(updates[SELL_EX][0], r.balance(SELL_EX), places=6)
        # сумма дельт по обеим ногам — это и есть net P&L сделки
        total_change = updates[BUY_EX][1] + updates[SELL_EX][1]
        self.assertAlmostEqual(total_change, res.trade.net_pnl, places=6)


if __name__ == "__main__":
    unittest.main()
