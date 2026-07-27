/**
 * Форматирование чисел и дат. Везде через Intl — раньше использовался
 * `toFixed()`, из-за чего суммы вида `$12345.67` шли без разделителей разрядов,
 * а даты — в неконтролируемой локали браузера.
 */

/**
 * Цена с адаптивной точностью: дешёвые мемкоины (BONK, SHIB) с ценой ~1e-5
 * при `toLocaleString()` округлялись до "0", скрывая реальную цену.
 */
export function formatPrice(value: number): string {
  if (!Number.isFinite(value) || value === 0) return '0'
  const abs = Math.abs(value)
  if (abs >= 1) return value.toLocaleString('en-US', { maximumFractionDigits: 2 })
  if (abs >= 0.01) return value.toLocaleString('en-US', { maximumFractionDigits: 4 })
  return value.toLocaleString('en-US', { maximumSignificantDigits: 4 })
}

/**
 * Цена исполнения (VWAP) — точнее formatPrice. Разложение P&L в карточке
 * сделки обязано сходиться: округление 8.6455 → «8.65» прятало всё
 * проскальзывание, и gross, посчитанный по top-of-book, «не бился» с ценами.
 */
export function formatExecPrice(value: number): string {
  if (!Number.isFinite(value) || value === 0) return '0'
  const abs = Math.abs(value)
  if (abs >= 1)
    return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
  return value.toLocaleString('en-US', { maximumSignificantDigits: 6 })
}

const USD = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

/**
 * Денежная сумма: `-$1,234.56` (минус перед знаком валюты, разряды разделены).
 * `signed` добавляет явный `+` — знак нужен там, где смысл иначе передаётся
 * только цветом (правило color-not-only).
 */
export function formatUsd(value: number, signed = false): string {
  if (!Number.isFinite(value)) return '—'
  const sign = value < 0 ? '-' : signed && value > 0 ? '+' : ''
  return `${sign}$${USD.format(Math.abs(value))}`
}

/** Процент с фиксированной точностью и явным знаком при необходимости. */
export function formatPct(value: number, digits = 2, signed = false): string {
  if (!Number.isFinite(value)) return '—'
  const sign = value < 0 ? '-' : signed && value > 0 ? '+' : ''
  return `${sign}${Math.abs(value).toFixed(digits)}%`
}

/** Целое количество с разделителями разрядов. */
export function formatCount(value: number): string {
  if (!Number.isFinite(value)) return '—'
  return value.toLocaleString('ru-RU')
}

/** Объём в базовой монете — до 6 знаков, лишние нули не показываем. */
export function formatAmount(value: number): string {
  if (!Number.isFinite(value)) return '—'
  return value.toLocaleString('en-US', { maximumFractionDigits: 6, minimumFractionDigits: 2 })
}

const DATE_TIME = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
})

const TIME_ONLY = new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' })

const DAY_MONTH = new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: 'short' })

function toDate(value: string | number): Date | null {
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

export function formatDateTime(value: string | number): string {
  const d = toDate(value)
  return d ? DATE_TIME.format(d) : '—'
}

export function formatTime(value: string | number): string {
  const d = toDate(value)
  return d ? TIME_ONLY.format(d) : '—'
}

export function formatDayMonth(value: string | number): string {
  const d = toDate(value)
  return d ? DAY_MONTH.format(d) : String(value)
}

/** Длительность в человекочитаемом виде: 850 ms → «850 мс», 4200 → «4.2 с». */
export function formatDuration(ms: number): string {
  if (!Number.isFinite(ms)) return '—'
  return ms < 1000 ? `${Math.round(ms)} мс` : `${(ms / 1000).toFixed(1)} с`
}
