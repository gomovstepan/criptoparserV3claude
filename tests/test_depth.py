"""Unit-тесты shared/depth.py (VWAP-проход по стакану).

Запускать ВНУТРИ любого контейнера, где смонтирован shared/ (scanner/executor).
    docker cp tests/test_depth.py arb-scanner:/app/
    docker exec arb-scanner python -m unittest test_depth -v
"""
import json
import unittest

from shared.depth import (
    DEPTH_MAX_AGE_MS,
    dump_depth,
    is_fresh,
    parse_depth,
    walk_asks_for_notional,
    walk_bids_for_amount,
)


class TestWalkAsks(unittest.TestCase):
    def test_one_level_covers_notional(self):
        # asks: 10 @ 100 — на $500 хватает первого уровня, VWAP = 100
        r = walk_asks_for_notional([[100.0, 10.0]], notional_usd=500.0)
        self.assertIsNotNone(r)
        amount, vwap = r
        self.assertAlmostEqual(amount, 5.0, places=6)
        self.assertAlmostEqual(vwap, 100.0, places=6)

    def test_walk_multiple_levels(self):
        # 5@100 (=500), потом 5@110 (=550). Купить на $1000 → 5 base + (500/110) base.
        asks = [[100.0, 5.0], [110.0, 5.0]]
        r = walk_asks_for_notional(asks, notional_usd=1000.0)
        self.assertIsNotNone(r)
        amount, vwap = r
        self.assertAlmostEqual(amount, 5.0 + 500.0 / 110.0, places=6)
        self.assertAlmostEqual(vwap, 1000.0 / amount, places=6)
        self.assertGreater(vwap, 100.0)  # хуже best ask
        self.assertLess(vwap, 110.0)     # но лучше топ 2-го уровня

    def test_insufficient_depth_returns_none(self):
        self.assertIsNone(walk_asks_for_notional([[100.0, 5.0]], notional_usd=1000.0))

    def test_empty_book_returns_none(self):
        self.assertIsNone(walk_asks_for_notional([], notional_usd=100.0))

    def test_zero_notional_returns_none(self):
        self.assertIsNone(walk_asks_for_notional([[100.0, 10.0]], notional_usd=0.0))


class TestWalkBids(unittest.TestCase):
    def test_one_level_covers_amount(self):
        r = walk_bids_for_amount([[100.0, 10.0]], amount_base=5.0)
        self.assertAlmostEqual(r, 100.0, places=6)

    def test_walk_multiple_bids_down(self):
        # продаём 8 base: 5 @ 100 + 3 @ 95 = 500 + 285 = 785 → VWAP = 785/8 = 98.125
        bids = [[100.0, 5.0], [95.0, 5.0]]
        r = walk_bids_for_amount(bids, amount_base=8.0)
        self.assertAlmostEqual(r, 785.0 / 8.0, places=6)
        self.assertLess(r, 100.0)
        self.assertGreater(r, 95.0)

    def test_insufficient_depth_returns_none(self):
        self.assertIsNone(walk_bids_for_amount([[100.0, 5.0]], amount_base=10.0))

    def test_zero_amount_returns_none(self):
        self.assertIsNone(walk_bids_for_amount([[100.0, 5.0]], amount_base=0.0))


class TestSerialization(unittest.TestCase):
    def test_dump_and_parse_roundtrip(self):
        bids = [[100.0, 5.0], [95.0, 5.0]]
        asks = [[101.0, 5.0], [110.0, 5.0]]
        raw = dump_depth(bids, asks, ts=1_700_000_000_000)
        d = parse_depth(raw)
        self.assertEqual(d["ts"], 1_700_000_000_000)
        self.assertEqual(d["bids"], bids)
        self.assertEqual(d["asks"], asks)

    def test_dump_truncates_to_levels(self):
        raw = dump_depth(
            bids=[[100.0, 1.0]] * 15,
            asks=[[101.0, 1.0]] * 15,
            ts=1, levels=10,
        )
        d = json.loads(raw)
        self.assertEqual(len(d["bids"]), 10)
        self.assertEqual(len(d["asks"]), 10)

    def test_parse_empty_returns_none(self):
        self.assertIsNone(parse_depth(None))
        self.assertIsNone(parse_depth(""))
        self.assertIsNone(parse_depth("not-json"))
        self.assertIsNone(parse_depth(json.dumps({"ts": 1, "bids": [], "asks": []})))


class TestFreshness(unittest.TestCase):
    def test_fresh_when_within_window(self):
        d = {"ts": 1_000_000, "bids": [[1, 1]], "asks": [[1, 1]]}
        self.assertTrue(is_fresh(d, now_ms=1_000_000 + DEPTH_MAX_AGE_MS - 1))

    def test_stale_when_over_window(self):
        d = {"ts": 1_000_000, "bids": [[1, 1]], "asks": [[1, 1]]}
        self.assertFalse(is_fresh(d, now_ms=1_000_000 + DEPTH_MAX_AGE_MS + 1))

    def test_none_is_not_fresh(self):
        self.assertFalse(is_fresh(None, now_ms=1_000_000))


if __name__ == "__main__":
    unittest.main()
