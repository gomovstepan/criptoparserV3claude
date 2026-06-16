"""Расчёт P&L симулированной арбитражной сделки (Фаза 7).

Slippage ухудшает обе ноги: покупка исполняется чуть выше ask, продажа — чуть
ниже bid. gross_pnl — идеальная разница цен без издержек; net_pnl учитывает
slippage, taker-комиссии обеих бирж и комиссию вывода.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PnLResult:
    amount: float
    effective_buy: float
    effective_sell: float
    buy_fee: float
    sell_fee: float
    withdrawal_fee: float
    slippage_cost: float
    gross_pnl: float
    net_pnl: float


def calculate_pnl(
    buy_price: float,
    sell_price: float,
    amount: float,
    buy_fee_pct: float,
    sell_fee_pct: float,
    withdrawal_fee: float,
    slippage_pct: float,
) -> PnLResult:
    """Посчитать издержки и P&L сделки на ``amount`` базового актива."""
    effective_buy = buy_price * (1 + slippage_pct / 100)
    effective_sell = sell_price * (1 - slippage_pct / 100)

    buy_cost = amount * effective_buy
    sell_proceeds = amount * effective_sell
    buy_fee = buy_cost * buy_fee_pct / 100
    sell_fee = sell_proceeds * sell_fee_pct / 100
    slippage_cost = amount * (buy_price + sell_price) * slippage_pct / 100

    gross_pnl = amount * (sell_price - buy_price)
    net_pnl = sell_proceeds - buy_cost - buy_fee - sell_fee - withdrawal_fee

    return PnLResult(
        amount=amount,
        effective_buy=effective_buy,
        effective_sell=effective_sell,
        buy_fee=buy_fee,
        sell_fee=sell_fee,
        withdrawal_fee=withdrawal_fee,
        slippage_cost=slippage_cost,
        gross_pnl=gross_pnl,
        net_pnl=net_pnl,
    )
