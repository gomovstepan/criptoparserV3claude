import { useId } from 'react'
import { Calendar } from 'lucide-react'
import { RANGE_PRESETS } from '../types'

/** Выбор периода аналитики через пресеты (отдаёт количество дней в API-параметр `days`). */
export default function DateRangePicker({
  days,
  onChange,
}: {
  days: number
  onChange: (days: number) => void
}) {
  const id = useId()
  return (
    // relative обязателен: внутри лежит .sr-only (position:absolute) — без
    // позиционированного предка он позиционируется от вьюпорта и расширяет
    // горизонтальную прокрутку страницы
    <div className="relative flex items-center gap-2">
      <label htmlFor={id} className="sr-only">
        Период аналитики
      </label>
      <div className="flex min-h-[44px] items-center gap-2 rounded-lg border border-edge-strong bg-surface2 px-3 text-sm text-ink focus-within:border-accent">
        <Calendar size={16} className="shrink-0 text-muted" aria-hidden="true" />
        <select
          id={id}
          value={days}
          onChange={(e) => onChange(Number(e.target.value))}
          className="min-h-[42px] bg-transparent pr-1 text-ink"
        >
          {RANGE_PRESETS.map((p) => (
            <option key={p.days} value={p.days} className="bg-surface2">
              {p.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
