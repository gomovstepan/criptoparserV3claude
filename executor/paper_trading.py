"""Движок paper-trading (Фаза 7 + глубина стакана).

Симулирует исполнение арбитражной возможности проходом по глубине стакана:
покупка «съедает» asks buy-биржи снизу вверх на плановый notional, продажа
съедает bids sell-биржи на полученный amount. Фактические цены исполнения —
VWAP уровней. Если глубины нет или она устарела — сделка пропускается.
Размер позиции — max_position_pct% от текущего баланса buy-биржи. Kill switch
мгновенно останавливает создание новых сделок.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

import redis.asyncio as redis
import structlog

from balance import get_balance, update_balance
from rebalance import RebalanceResult, maybe_rebalance
from shared.depth import (
    DEPTH_MAX_AGE_MS, depth_key, is_fresh, parse_depth,
    walk_asks_for_notional, walk_bids_for_amount,
)
from shared.models import Opportunity, Trade

MIN_NOTIONAL_USDT = 10.0  # сделки меньше — пропускаем (недостаточно средств)

_log = structlog.get_logger()


@dataclass
class ExecutionResult:
    trade: Trade
    balance_updates: list[tuple[str, float, float]]  # (exchange, new_balance, change)
    rebalance: RebalanceResult | None = None


class PaperTradingEngine:
    def __init__(self, redis_client: redis.Redis, max_position_pct: float = 10.0,
                 rebalance_threshold: float = 100.0) -> None:
        self._redis = redis_client
        self.max_position_pct = max_position_pct
        self.rebalance_threshold = rebalance_threshold
        self.kill_switch = False

    async def execute_opportunity(self, opp: Opportunity) -> ExecutionResult | None:
        """Симулировать сделку. None — kill switch или недостаточно средств."""
        if self.kill_switch:
            return None

        start = time.time()
        buy_balance = await get_balance(self._redis, opp.buy_exchange)

        rebalance_result = await maybe_rebalance(
            self._redis, opp.buy_exchange, buy_balance, self.rebalance_threshold,
        )
        if rebalance_result is not None:
            buy_balance = rebalance_result.receiver_new_balance
        elif buy_balance <= self.rebalance_threshold:
            return None

        notional = buy_balance * self.max_position_pct / 100.0  # ≤ 10% баланса
        if notional < MIN_NOTIONAL_USDT:
            return None

        now_ms = int(time.time() * 1000)
        raw_buy, raw_sell = await self._redis.mget([
            depth_key(opp.buy_exchange, opp.symbol),
            depth_key(opp.sell_exchange, opp.symbol),
        ])
        buy_depth, sell_depth = parse_depth(raw_buy), parse_depth(raw_sell)
        if not is_fresh(buy_depth, now_ms, DEPTH_MAX_AGE_MS) \
                or not is_fresh(sell_depth, now_ms, DEPTH_MAX_AGE_MS):
            _log.info(
                "trade_skipped_stale_depth",
                symbol=opp.symbol, buy_ex=opp.buy_exchange, sell_ex=opp.sell_exchange,
            )
            return None

        walked_buy = walk_asks_for_notional(buy_depth["asks"], notional)
        if walked_buy is None:
            _log.info("trade_skipped_thin_buy_book",
                      symbol=opp.symbol, exchange=opp.buy_exchange, notional=notional)
            return None
        amount, effective_buy = walked_buy

        effective_sell = walk_bids_for_amount(sell_depth["bids"], amount)
        if effective_sell is None:
            _log.info("trade_skipped_thin_sell_book",
                      symbol=opp.symbol, exchange=opp.sell_exchange, amount=amount)
            return None

        top_ask = float(buy_depth["asks"][0][0])
        top_bid = float(sell_depth["bids"][0][0])

        buy_cost = amount * effective_buy
        sell_proceeds = amount * effective_sell
        buy_fee_abs = buy_cost * opp.buy_fee_pct / 100
        sell_fee_abs = sell_proceeds * opp.sell_fee_pct / 100
        gross_pnl = amount * (top_bid - top_ask)
        net_pnl = sell_proceeds - buy_cost - buy_fee_abs - sell_fee_abs
        slippage_cost = amount * ((effective_buy - top_ask) + (top_bid - effective_sell))

        buy_change = -(buy_cost + buy_fee_abs)
        sell_change = sell_proceeds - sell_fee_abs
        new_buy = await update_balance(self._redis, opp.buy_exchange, buy_change)
        new_sell = await update_balance(self._redis, opp.sell_exchange, sell_change)

        now = int(time.time() * 1000)
        trade = Trade(
            id=f"trade_{now}_{uuid.uuid4().hex[:8]}",
            opportunity_id=opp.id,
            symbol=opp.symbol,
            buy_exchange=opp.buy_exchange,
            sell_exchange=opp.sell_exchange,
            buy_price=effective_buy,
            sell_price=effective_sell,
            amount=amount,
            buy_fee=buy_fee_abs,
            sell_fee=sell_fee_abs,
            withdrawal_fee=0.0,
            slippage_cost=slippage_cost,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            status="completed",
            executed_at=now,
            duration_ms=int((time.time() - start) * 1000),
        )
        return ExecutionResult(
            trade=trade,
            balance_updates=[
                (opp.buy_exchange, max(0.0, new_buy), buy_change),
                (opp.sell_exchange, max(0.0, new_sell), sell_change),
            ],
            rebalance=rebalance_result,
        )
