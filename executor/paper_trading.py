"""Движок paper-trading (Фаза 7).

Симулирует исполнение арбитражной возможности: покупка на buy_exchange, продажа
на sell_exchange, расчёт P&L со slippage и комиссиями, обновление виртуальных
балансов. Размер позиции — max_position_pct% от текущего баланса buy-биржи
(self-limiting: баланс не уходит в ноль). Kill switch мгновенно останавливает
создание новых сделок.
"""
from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass

import redis.asyncio as redis

from balance import get_balance, update_balance
from pnl import calculate_pnl
from shared.config import EXCHANGES
from shared.models import Opportunity, Trade

MIN_NOTIONAL_USDT = 10.0  # сделки меньше — пропускаем (недостаточно средств)


@dataclass
class ExecutionResult:
    trade: Trade
    balance_updates: list[tuple[str, float, float]]  # (exchange, new_balance, change)


class PaperTradingEngine:
    def __init__(self, redis_client: redis.Redis, max_position_pct: float = 10.0) -> None:
        self._redis = redis_client
        self.max_position_pct = max_position_pct
        self.kill_switch = False

    async def execute_opportunity(self, opp: Opportunity) -> ExecutionResult | None:
        """Симулировать сделку. None — kill switch или недостаточно средств."""
        if self.kill_switch:
            return None

        start = time.time()
        buy_balance = await get_balance(self._redis, opp.buy_exchange)
        notional = buy_balance * self.max_position_pct / 100.0  # ≤ 10% баланса
        if notional < MIN_NOTIONAL_USDT:
            return None

        amount = notional / opp.buy_price
        slippage_pct = random.uniform(0.1, 0.3)
        withdrawal_fee = EXCHANGES[opp.sell_exchange].withdrawal_usdt

        pnl = calculate_pnl(
            opp.buy_price, opp.sell_price, amount,
            opp.buy_fee_pct, opp.sell_fee_pct, withdrawal_fee, slippage_pct,
        )

        buy_change = -(amount * pnl.effective_buy + pnl.buy_fee)
        sell_change = amount * pnl.effective_sell - pnl.sell_fee - pnl.withdrawal_fee
        new_buy = await update_balance(self._redis, opp.buy_exchange, buy_change)
        new_sell = await update_balance(self._redis, opp.sell_exchange, sell_change)

        now = int(time.time() * 1000)
        trade = Trade(
            id=f"trade_{now}_{uuid.uuid4().hex[:8]}",
            opportunity_id=opp.id,
            symbol=opp.symbol,
            buy_exchange=opp.buy_exchange,
            sell_exchange=opp.sell_exchange,
            buy_price=opp.buy_price,
            sell_price=opp.sell_price,
            amount=amount,
            buy_fee=pnl.buy_fee,
            sell_fee=pnl.sell_fee,
            withdrawal_fee=pnl.withdrawal_fee,
            slippage_cost=pnl.slippage_cost,
            gross_pnl=pnl.gross_pnl,
            net_pnl=pnl.net_pnl,
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
        )
