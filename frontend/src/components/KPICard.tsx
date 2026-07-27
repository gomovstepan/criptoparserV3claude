import type { LucideIcon } from 'lucide-react'
import { cn } from '../lib/utils'
import Tooltip from './Tooltip'

/**
 * Карточка ключевой метрики.
 * Размер значения уменьшается на узких экранах — иначе суммы вроде
 * `-$12,345.67` вылезали из карточки при 375px в сетке из двух колонок.
 */
export default function KPICard({
  title,
  value,
  icon: Icon,
  accent = 'default',
  tooltip,
  hint,
}: {
  title: string
  value: string
  icon: LucideIcon
  accent?: 'pos' | 'neg' | 'default'
  tooltip?: string
  hint?: string
}) {
  return (
    <div className="rounded-xl border border-edge bg-surface p-4">
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-muted">
          {tooltip ? <Tooltip text={tooltip}>{title}</Tooltip> : title}
        </span>
        <Icon size={18} className="shrink-0 text-muted" aria-hidden="true" />
      </div>
      <div
        className={cn(
          'mt-2 break-all text-xl font-semibold tabular-nums sm:text-2xl',
          accent === 'pos' ? 'text-success' : accent === 'neg' ? 'text-danger' : 'text-ink',
        )}
      >
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  )
}
