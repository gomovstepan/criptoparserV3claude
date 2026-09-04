/**
 * Форматирование цены с адаптивной точностью: дешёвые мемкоины (BONK, SHIB)
 * с ценой ~1e-5 при `toLocaleString()` округлялись до "0", скрывая реальную цену.
 */
export function formatPrice(value: number): string {
  if (!Number.isFinite(value) || value === 0) return '0'
  const abs = Math.abs(value)
  if (abs >= 1) return value.toLocaleString(undefined, { maximumFractionDigits: 2 })
  if (abs >= 0.01) return value.toLocaleString(undefined, { maximumFractionDigits: 4 })
  return value.toLocaleString(undefined, { maximumSignificantDigits: 4 })
}
