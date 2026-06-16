"""Расчёт межбиржевых спредов по одной паре.

Для каждой упорядоченной пары бирж (A=buy, B=sell): покупаем по ask на A,
продаём по bid на B. gross_spread = (sell_price - buy_price) / buy_price * 100.
net_spread дополнительно учитывает taker-комиссии обеих бирж и комиссию вывода.
"""
from __future__ import annotations

import time

from shared.config import EXCHANGES
from shared.models import Opportunity


def calculate_spreads(
    symbol: str,
    prices: dict[str, dict[str, float]],
    min_spread_pct: float,
) -> list[Opportunity]:
    """Вернуть opportunities по символу, где gross_spread >= min_spread_pct.

    ``prices`` — отображение exchange → {"bid": .., "ask": ..} (последние цены).
    """
    opportunities: list[Opportunity] = []
    exchanges = [ex for ex in prices if ex in EXCHANGES]
    now = int(time.time() * 1000)

    for buy_ex in exchanges:
        buy_price = prices[buy_ex].get("ask", 0.0)        # покупаем по ask
        if buy_price <= 0:
            continue
        for sell_ex in exchanges:
            if sell_ex == buy_ex:
                continue
            sell_price = prices[sell_ex].get("bid", 0.0)  # продаём по bid
            if sell_price <= 0:
                continue

            gross = (sell_price - buy_price) / buy_price * 100
            if gross < min_spread_pct:
                continue

            buy_fee = EXCHANGES[buy_ex].taker_fee_pct
            sell_fee = EXCHANGES[sell_ex].taker_fee_pct
            withdrawal_usd = EXCHANGES[sell_ex].withdrawal_usdt
            withdrawal_pct = withdrawal_usd / buy_price * 100
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
