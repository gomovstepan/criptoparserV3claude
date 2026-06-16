import type { Opportunity, Trade } from '../types'

/** Преобразование сырых строковых полей Redis Stream (из WS) в типизированные объекты. */
export function normalizeOpportunity(d: Record<string, string>): Opportunity {
  return {
    id: d.id,
    symbol: d.symbol,
    buy_exchange: d.buy_exchange,
    sell_exchange: d.sell_exchange,
    buy_price: parseFloat(d.buy_price),
    sell_price: parseFloat(d.sell_price),
    gross_spread_pct: parseFloat(d.gross_spread_pct),
    net_spread_pct: parseFloat(d.net_spread_pct),
    detected_at: new Date(parseInt(d.detected_at, 10)).toISOString(),
  }
}

export function normalizeTrade(d: Record<string, string>): Trade {
  return {
    id: d.id,
    symbol: d.symbol,
    buy_exchange: d.buy_exchange,
    sell_exchange: d.sell_exchange,
    amount: parseFloat(d.amount),
    gross_pnl: parseFloat(d.gross_pnl),
    net_pnl: parseFloat(d.net_pnl),
    status: d.status,
    executed_at: d.executed_at ? new Date(parseInt(d.executed_at, 10)).toISOString() : '',
  }
}
