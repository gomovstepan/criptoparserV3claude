"""Расчёт межбиржевых спредов по одной паре.

Для каждой упорядоченной пары бирж (A=buy, B=sell): покупаем по ask на A,
продаём по bid на B. Если известна глубина стакана обеих бирж — считаем
исполнимые VWAP-цены на плановый notional и используем их как buy/sell.
Иначе fallback на top-of-book. Спред считается по буквальным ценам
исполнения; net дополнительно учитывает taker-комиссии обеих бирж и
комиссию вывода.
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
) -> list[Opportunity]:
    """Вернуть opportunities по символу, где gross_spread >= min_spread_pct.

    ``prices`` — exchange → {"bid": .., "ask": ..} (последние цены, fallback).
    ``depth``  — exchange → {"ts", "bids": [[p,q]...], "asks": [[p,q]...]} (топ-N).
                 Если для обеих бирж пары есть свежая глубина — считаем VWAP
                 на ``estimated_notional_usd``; иначе — по top-of-book.
    """
    opportunities: list[Opportunity] = []
    exchanges = [ex for ex in prices if ex in EXCHANGES]
    now = int(time.time() * 1000)
    depth = depth or {}

    for buy_ex in exchanges:
        top_ask = prices[buy_ex].get("ask", 0.0)
        if top_ask <= 0:
            continue
        for sell_ex in exchanges:
            if sell_ex == buy_ex:
                continue
            top_bid = prices[sell_ex].get("bid", 0.0)
            if top_bid <= 0:
                continue

            buy_price, sell_price = top_ask, top_bid
            buy_depth, sell_depth = depth.get(buy_ex), depth.get(sell_ex)
            if buy_depth and sell_depth:
                walked_buy = walk_asks_for_notional(buy_depth["asks"], estimated_notional_usd)
                if walked_buy is None:
                    continue  # глубины на buy-стороне не хватает — фантомный спред
                amount, vwap_buy = walked_buy
                vwap_sell = walk_bids_for_amount(sell_depth["bids"], amount)
                if vwap_sell is None:
                    continue  # на sell-стороне не хватает — тоже фантом
                buy_price, sell_price = vwap_buy, vwap_sell

            gross = (sell_price - buy_price) / buy_price * 100
            if gross < min_spread_pct:
                continue

            buy_fee = EXCHANGES[buy_ex].taker_fee_pct
            sell_fee = EXCHANGES[sell_ex].taker_fee_pct
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
