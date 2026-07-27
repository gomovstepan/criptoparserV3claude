export interface Opportunity {
  id: string
  symbol: string
  buy_exchange: string
  sell_exchange: string
  buy_price: number
  sell_price: number
  gross_spread_pct: number
  // net_spread_pct — display-only: вычитает комиссию вывода, размазанную на
  // один notional (~40x пессимистичнее фактического списания при ребалансе).
  // Для фильтров/бейджей используется net_fees_pct = gross − обе taker-комиссии.
  net_spread_pct: number
  buy_fee_pct?: number
  sell_fee_pct?: number
  net_fees_pct?: number
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
  // Разложение P&L: net = gross − slippage − buy_fee − sell_fee.
  buy_fee?: number
  sell_fee?: number
  slippage_cost?: number
  // Top-of-book на момент исполнения (null у сделок до миграции).
  buy_top_ask?: number | null
  sell_top_bid?: number | null
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

/** Описание полей формы настроек (ключ в `settings` → подпись/единица/шаг). */
export const SETTING_FIELDS: {
  key: string
  label: string
  unit: string
  step: number
  hint: string
  /** Бэкенд допускает отрицательное значение (см. SettingsUpdate в exchanges.py). */
  allowNegative?: boolean
}[] = [
  // Здесь только настройки, которые сервисы реально читают. Раньше форма
  // показывала ещё slippage_tolerance_pct, execution_timeout_sec и
  // daily_loss_limit_pct — они сохранялись в БД, но не читались ни одним
  // сервисом (дневной лимит убытка — нереализованное требование ТЗ E-014).
  // Возвращать поле сюда можно только вместе с кодом, который его использует,
  // и с ключом в allowlist PUT /api/v1/settings (роутер exchanges.py).
  { key: 'min_spread_pct', label: 'Мин. спред (gross)', unit: '%', step: 0.01, hint: 'Грубый префильтр opportunity по gross-спреду' },
  { key: 'min_net_spread_pct', label: 'Мин. net-спред', unit: '%', step: 0.01, hint: 'Фильтр по спреду за вычетом taker-комиссий обеих бирж' },
  { key: 'max_position_pct', label: 'Макс. позиция', unit: '%', step: 0.5, hint: '% от баланса биржи на сделку' },
  // allowNegative: оператор может сознательно допустить мелкий минус в paper-режиме,
  // чтобы наблюдать поток сделок (бэкенд разрешает от -1000).
  { key: 'min_profit_usd', label: 'Мин. прибыль сделки', unit: '$', step: 0.1, hint: 'Executor не исполняет сделку с net P&L ниже порога', allowNegative: true },
  { key: 'loss_cooldown_sec', label: 'Кулдаун после убытка', unit: 'с', step: 10, hint: 'Пауза для связки после убыточной оценки (0 — выкл.)' },
  { key: 'depth_max_age_ms_executor', label: 'Свежесть стакана (executor)', unit: 'мс', step: 100, hint: 'Старше — сделка пропускается' },
  { key: 'depth_max_age_ms_scanner', label: 'Свежесть стакана (scanner)', unit: 'мс', step: 100, hint: 'Старше — пара не сканируется' },
  { key: 'notification_spread_threshold', label: 'Порог алерта (спред)', unit: '%', step: 0.05, hint: 'Min спред для Telegram' },
  { key: 'notification_trade_min_pnl', label: 'Порог алерта (сделка)', unit: '$', step: 1, hint: 'Min |net P&L| для Telegram' },
]

export const EXCHANGE_LIST = ['binance', 'bybit', 'kucoin', 'gateio', 'bitget', 'coinex', 'bingx']
export const SYMBOLS = [
  'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
  'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'DOGE/USDT', 'SHIB/USDT',
  'LTC/USDT', 'LINK/USDT', 'UNI/USDT', 'NEAR/USDT', 'ARB/USDT',
  'OP/USDT', 'APT/USDT', 'SUI/USDT', 'INJ/USDT', 'IMX/USDT',
  'TIA/USDT', 'SEI/USDT', 'TON/USDT', 'ENA/USDT', 'WLD/USDT',
  'ZEC/USDT', 'XMR/USDT', 'PYTH/USDT', 'BLUR/USDT', 'AEVO/USDT',
  'PEPE/USDT', 'BONK/USDT', 'WIF/USDT', 'FLOKI/USDT', 'MEME/USDT',
  'PENGU/USDT', 'HTX/USDT',
]
// В paper-режиме executor записывает только 'completed' (paper_trading.py
// хардкодит статус). failed/pending/cancelled зарезервированы схемой БД,
// но кодом не создаются — фильтр их не предлагает, чтобы не обещать пустых
// выборок. Расширять список только вместе с кодом, который пишет эти статусы.
export const TRADE_STATUSES = ['completed']

export const RANGE_PRESETS: { label: string; days: number }[] = [
  { label: 'Последние 24 часа', days: 1 },
  { label: 'Последние 7 дней', days: 7 },
  { label: 'Последние 30 дней', days: 30 },
  { label: 'Последние 90 дней', days: 90 },
]
