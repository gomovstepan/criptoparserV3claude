"""Расчёт P&L симулированной арбитражной сделки.

Здесь живёт единственная формула расчёта, которой пользуется движок
``paper_trading.PaperTradingEngine``. Раньше в этом модуле лежала устаревшая
процентная модель slippage (``buy_price * (1 + slippage_pct / 100)``), которую не
вызывал никто, кроме собственного теста, — а настоящая арифметика была вписана
прямо в ``execute_opportunity`` и не покрывалась ничем.

Модель издержек:

- Цены исполнения — VWAP прохода по стакану (``shared/depth.py``); их считает
  вызывающий код и передаёт сюда как ``effective_buy`` / ``effective_sell``.
- ``gross_pnl`` — по top-of-book: сколько дала бы сделка, влезь весь объём в
  лучшую цену. Это «идеальный» ориентир.
- ``slippage_cost`` — разница между VWAP и top-of-book по обеим ногам. Величина
  отчётная: она уже сидит внутри ``effective_*``, поэтому повторно из ``net_pnl``
  не вычитается. По построению неотрицательна.
- Комиссия вывода в ``net_pnl`` НЕ входит: она списывается один раз при
  ребалансе (``executor/rebalance.py``). См. инвариант в CLAUDE.md.

Выполняется тождество ``net_pnl == gross_pnl - slippage_cost - buy_fee - sell_fee``.
Чистый stdlib, без зависимостей — тест гоняется внутри контейнера executor.
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
    slippage_cost: float
    gross_pnl: float
    net_pnl: float


def settle_trade(
    amount: float,
    effective_buy: float,
    effective_sell: float,
    top_ask: float,
    top_bid: float,
    buy_fee_pct: float,
    sell_fee_pct: float,
) -> PnLResult:
    """Посчитать издержки и P&L по уже определённым ценам исполнения.

    ``effective_buy`` / ``effective_sell`` — VWAP прохода по стакану на ``amount``
    базового актива; ``top_ask`` / ``top_bid`` — лучшие цены тех же стаканов.
    """
    buy_cost = amount * effective_buy
    sell_proceeds = amount * effective_sell
    buy_fee = buy_cost * buy_fee_pct / 100
    sell_fee = sell_proceeds * sell_fee_pct / 100

    gross_pnl = amount * (top_bid - top_ask)
    net_pnl = sell_proceeds - buy_cost - buy_fee - sell_fee
    slippage_cost = amount * ((effective_buy - top_ask) + (top_bid - effective_sell))

    return PnLResult(
        amount=amount,
        effective_buy=effective_buy,
        effective_sell=effective_sell,
        buy_fee=buy_fee,
        sell_fee=sell_fee,
        slippage_cost=slippage_cost,
        gross_pnl=gross_pnl,
        net_pnl=net_pnl,
    )
