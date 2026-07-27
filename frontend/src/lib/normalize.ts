import type { Opportunity, Trade } from '../types'

/** Число из строки Redis Stream; NaN вместо падения на пустом/битом поле. */
function num(raw: string | undefined): number {
  const v = parseFloat(raw ?? '')
  return Number.isFinite(v) ? v : NaN
}

/**
 * Epoch ms из строки в ISO.
 * `new Date(NaN).toISOString()` бросает RangeError — на битом поле весь
 * обработчик WS-сообщения падал (ошибка глушилась catch'ем, сообщение терялось).
 */
function isoFromEpoch(raw: string | undefined): string {
  const ms = parseInt(raw ?? '', 10)
  return Number.isFinite(ms) ? new Date(ms).toISOString() : ''
}

/** Число или undefined — для опциональных полей стрима (не хотим NaN в типе). */
function optNum(raw: string | undefined): number | undefined {
  const v = parseFloat(raw ?? '')
  return Number.isFinite(v) ? v : undefined
}

/** Преобразование сырых строковых полей Redis Stream (из WS) в типизированные объекты. */
export function normalizeOpportunity(d: Record<string, string>): Opportunity {
  const gross = num(d.gross_spread_pct)
  const buyFee = optNum(d.buy_fee_pct)
  const sellFee = optNum(d.sell_fee_pct)
  return {
    id: d.id,
    symbol: d.symbol,
    buy_exchange: d.buy_exchange,
    sell_exchange: d.sell_exchange,
    buy_price: num(d.buy_price),
    sell_price: num(d.sell_price),
    gross_spread_pct: gross,
    net_spread_pct: num(d.net_spread_pct),
    buy_fee_pct: buyFee,
    sell_fee_pct: sellFee,
    // Честный net (без комиссии вывода) — тот же расчёт, что в REST-ответе.
    net_fees_pct:
      buyFee !== undefined && sellFee !== undefined && Number.isFinite(gross)
        ? gross - buyFee - sellFee
        : undefined,
    detected_at: isoFromEpoch(d.detected_at),
  }
}

export function normalizeTrade(d: Record<string, string>): Trade {
  return {
    id: d.id,
    symbol: d.symbol,
    buy_exchange: d.buy_exchange,
    sell_exchange: d.sell_exchange,
    amount: num(d.amount),
    gross_pnl: num(d.gross_pnl),
    net_pnl: num(d.net_pnl),
    status: d.status,
    executed_at: isoFromEpoch(d.executed_at),
    opportunity_id: d.opportunity_id || undefined,
    buy_price: optNum(d.buy_price),
    sell_price: optNum(d.sell_price),
    buy_fee: optNum(d.buy_fee),
    sell_fee: optNum(d.sell_fee),
    slippage_cost: optNum(d.slippage_cost),
    buy_top_ask: optNum(d.buy_top_ask) ?? null,
    sell_top_bid: optNum(d.sell_top_bid) ?? null,
    duration_ms: optNum(d.duration_ms) ?? null,
  }
}
