"""Расчёт межбиржевых спредов по одной паре.

Для каждой упорядоченной пары бирж (A=buy, B=sell): покупаем по ask на A,
продаём по bid на B. Цены исполнения — ТОЛЬКО исполнимые VWAP по свежей
глубине обеих бирж на плановый notional. Fallback на top-of-book удалён
сознательно: он включался ровно тогда, когда фильтр глубины нужнее всего
(лаг/обрыв фида), и публиковал фантомные спреды от dust-ордеров на топе
книги — все убыточные сделки в истории системы родились этим путём.
Нет свежей глубины с обеих сторон — нет opportunity.

Два порога:
- ``min_spread_pct``     — грубый префильтр по gross-спреду;
- ``min_net_spread_pct`` — фильтр по net после taker-комиссий обеих бирж.
  Комиссия вывода в него НЕ входит: по модели ledger'а она списывается один
  раз при ребалансе, а не за сделку (см. CLAUDE.md, P&L invariant).

Поле ``net_spread_pct`` в Opportunity остаётся display-only: оно дополнительно
вычитает комиссию вывода, размазанную на один notional (~40x пессимистичнее
фактического списания), и НЕ используется как критерий ни здесь, ни в executor.
"""
from __future__ import annotations

import time

from shared.config import EXCHANGES
from shared.depth import walk_asks_for_notional, walk_bids_for_amount
from shared.models import Opportunity


def calculate_spreads(
    symbol: str,
    prices: dict[str, dict[str, float]],
    min_spread_pct: float,
    estimated_notional_usd: float = 1000.0,
    depth: dict[str, dict] | None = None,
    min_net_spread_pct: float = 0.0,
) -> list[Opportunity]:
    """Вернуть opportunities по символу с исполнимым VWAP-спредом.

    ``prices`` — exchange → {"bid": .., "ask": ..} (перечень активных бирж).
    ``depth``  — exchange → {"ts", "bids": [[p,q]...], "asks": [[p,q]...]} (топ-N,
                 только СВЕЖИЕ книги — фильтрует вызывающий код). Биржа без
                 записи в ``depth`` в расчёте не участвует.
    """
    opportunities: list[Opportunity] = []
    depth = depth or {}
    exchanges = [ex for ex in prices if ex in EXCHANGES and ex in depth]
    now = int(time.time() * 1000)

    for buy_ex in exchanges:
        walked_buy = walk_asks_for_notional(depth[buy_ex]["asks"], estimated_notional_usd)
        if walked_buy is None:
            continue  # глубины на buy-стороне не хватает — фантомный спред
        amount, buy_price = walked_buy

        for sell_ex in exchanges:
            if sell_ex == buy_ex:
                continue
            sell_price = walk_bids_for_amount(depth[sell_ex]["bids"], amount)
            if sell_price is None:
                continue  # на sell-стороне не хватает — тоже фантом

            gross = (sell_price - buy_price) / buy_price * 100
            if gross < min_spread_pct:
                continue

            buy_fee = EXCHANGES[buy_ex].taker_fee_pct
            sell_fee = EXCHANGES[sell_ex].taker_fee_pct
            if gross - buy_fee - sell_fee < min_net_spread_pct:
                continue  # спред не покрывает комиссии обеих ног

            withdrawal_usd = EXCHANGES[sell_ex].withdrawal_usdt
            withdrawal_pct = withdrawal_usd / estimated_notional_usd * 100
            net = gross - buy_fee - sell_fee - withdrawal_pct

            opportunities.append(Opportunity(
                id=f"opp_{now}_{buy_ex}_{sell_ex}_{symbol.replace('/', '').lower()}",
                symbol=symbol,
                buy_exchange=buy_ex,
                sell_exchange=sell_ex,
                buy_price=buy_price,
                sell_price=sell_price,
                gross_spread_pct=round(gross, 4),
                buy_fee_pct=buy_fee,
                sell_fee_pct=sell_fee,
                withdrawal_fee_usd=withdrawal_usd,
                net_spread_pct=round(net, 4),
                detected_at=now,
            ))
    return opportunities
