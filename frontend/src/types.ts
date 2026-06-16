export interface Opportunity {
  id: string
  symbol: string
  buy_exchange: string
  sell_exchange: string
  buy_price: number
  sell_price: number
  gross_spread_pct: number
  net_spread_pct: number
  detected_at: string
}

export interface Trade {
  id: string
  symbol: string
  buy_exchange: string
  sell_exchange: string
  amount: number
  gross_pnl: number
  net_pnl: number
  status: string
  executed_at: string
  // Поля присутствуют в REST-ответе /trades (для detail drawer); из WS их может не быть.
  opportunity_id?: string
  buy_price?: number
  sell_price?: number
  duration_ms?: number | null
}

export interface ExchangeStatus {
  exchange: string
  status: 'connected' | 'stale' | 'disconnected'
  latency_ms: number | null
  last_tick: string | null
}

export interface Stats {
  total_pnl: number
  trades_today: number
  pnl_today: number
  active_opportunities: number
  best_spread_pct: number
}

export interface PnLPoint {
  time: string
  pnl: number
  cumulative: number
}

export interface DailyPoint {
  date: string
  trades: number
  net_pnl: number
  gross_pnl: number
  cumulative_net_pnl: number
}

export interface AnalyticsSummary {
  period: string
  days: number
  total_trades: number
  winning_trades: number
  win_rate: number
  total_gross_pnl: number
  total_net_pnl: number
  avg_net_pnl: number
  avg_trade_duration_ms: number
  best_trade: number
  worst_trade: number
  daily: DailyPoint[]
}

export interface ExchangeConfig {
  exchange: string
  is_active: boolean
  maker_fee_pct: number
  taker_fee_pct: number
  withdrawal_btc: number | null
  withdrawal_usdt: number | null
  rate_limit_req_per_sec: number | null
}

export type ExchangeConnStatus = 'connected' | 'stale' | 'disconnected'

export interface SettingsMap {
  min_spread_pct: number
  max_position_pct: number
  slippage_tolerance_pct: number
  execution_timeout_sec: number
  daily_loss_limit_pct: number
  notification_spread_threshold: number
  notification_trade_min_pnl: number
  [key: string]: number | string | boolean
}

/** Описание полей формы настроек (ключ в `settings` → подпись/единица/шаг). */
export const SETTING_FIELDS: {
  key: string
  label: string
  unit: string
  step: number
  hint: string
}[] = [
  { key: 'min_spread_pct', label: 'Мин. спред', unit: '%', step: 0.01, hint: 'Порог для создания opportunity' },
  { key: 'max_position_pct', label: 'Макс. позиция', unit: '%', step: 0.5, hint: '% от баланса биржи на сделку' },
  { key: 'slippage_tolerance_pct', label: 'Slippage', unit: '%', step: 0.05, hint: 'Допустимое проскальзывание' },
  { key: 'execution_timeout_sec', label: 'Таймаут исполнения', unit: 'сек', step: 1, hint: 'Макс. время на сделку' },
  { key: 'daily_loss_limit_pct', label: 'Дневной лимит убытка', unit: '%', step: 0.5, hint: 'Стоп торговли за день' },
  { key: 'notification_spread_threshold', label: 'Порог алерта (спред)', unit: '%', step: 0.05, hint: 'Min спред для Telegram' },
  { key: 'notification_trade_min_pnl', label: 'Порог алерта (сделка)', unit: '$', step: 1, hint: 'Min |net P&L| для Telegram' },
]

export const EXCHANGE_LIST = ['binance', 'bybit', 'kucoin', 'gateio', 'bitget', 'coinex', 'bingx']
export const SYMBOLS = ['BTC/USDT', 'ETH/USDT']
export const TRADE_STATUSES = ['completed', 'failed', 'pending', 'cancelled']

export const RANGE_PRESETS: { label: string; days: number }[] = [
  { label: 'Последние 24 часа', days: 1 },
  { label: 'Последние 7 дней', days: 7 },
  { label: 'Последние 30 дней', days: 30 },
  { label: 'Последние 90 дней', days: 90 },
]
