import { useId } from 'react'

/**
 * Выпадающий список-фильтр.
 * Явная связь label↔select через id/htmlFor, видимый фокус (убран `outline-none`
 * без замены), высота 44px и граница edge-strong (≥3:1 к фону в обеих темах).
 */
export default function Select({
  label,
  value,
  onChange,
  options,
  allLabel = 'Все',
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: string[]
  allLabel?: string
}) {
  const id = useId()
  return (
    <div className="flex min-w-[9rem] flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-muted">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="min-h-[44px] rounded-lg border border-edge-strong bg-surface2 px-3 py-2 text-sm text-ink transition-colors duration-fast hover:border-accent"
      >
        <option value="">{allLabel}</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  )
}
