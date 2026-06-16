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
  return (
    <label className="flex items-center gap-2 rounded-lg border border-edge bg-surface2 px-3 py-2 text-sm text-ink">
      <Calendar size={16} className="text-muted" />
      <select
        value={days}
        onChange={(e) => onChange(Number(e.target.value))}
        className="bg-transparent text-ink outline-none"
      >
        {RANGE_PRESETS.map((p) => (
          <option key={p.days} value={p.days} className="bg-surface2">
            {p.label}
          </option>
        ))}
      </select>
    </label>
  )
}
