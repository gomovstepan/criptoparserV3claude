"""Форматирование Telegram-сообщений (Фаза 8). Plain text + эмодзи."""
from __future__ import annotations

from datetime import datetime, timezone

from shared.models import Opportunity, Trade


def _price(value: float) -> str:
    return f"${value:,.2f}"


def _utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def format_opportunity(opp: Opportunity) -> str:
    return (
        "🚨 Arbitrage Opportunity Detected!\n\n"
        f"Pair: {opp.symbol}\n"
        f"Buy: {opp.buy_exchange.title()} @ {_price(opp.buy_price)}\n"
        f"Sell: {opp.sell_exchange.title()} @ {_price(opp.sell_price)}\n\n"
        f"Spread: {opp.gross_spread_pct:.3f}%\n"
        f"Net Spread: {opp.net_spread_pct:.3f}%\n\n"
        f"⏱ Detected: {_utc(opp.detected_at)}"
    )


def format_trade(trade: Trade) -> str:
    emoji = "🟢" if trade.net_pnl >= 0 else "🔴"
    return (
        f"{emoji} Paper Trade Executed\n\n"
        f"Pair: {trade.symbol}\n"
        f"Buy: {trade.buy_exchange.title()} @ {_price(trade.buy_price)}\n"
        f"Sell: {trade.sell_exchange.title()} @ {_price(trade.sell_price)}\n"
        f"Amount: {trade.amount:.6f}\n\n"
        f"Gross P&L: {_price(trade.gross_pnl)}\n"
        f"Net P&L: {_price(trade.net_pnl)}\n"
        f"Status: {trade.status}"
    )
