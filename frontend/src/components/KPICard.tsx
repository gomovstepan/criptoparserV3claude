import type { LucideIcon } from 'lucide-react'
import { cn } from '../lib/utils'
import Tooltip from './Tooltip'

export default function KPICard({
  title,
  value,
  icon: Icon,
  accent = 'default',
  tooltip,
}: {
  title: string
  value: string
  icon: LucideIcon
  accent?: 'pos' | 'neg' | 'default'
  tooltip?: string
}) {
  const label = tooltip ? <Tooltip text={tooltip}>{title}</Tooltip> : title
  return (
    <div className="rounded-xl border border-edge bg-surface p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-muted">{label}</span>
        <Icon size={18} className="text-muted" />
      </div>
      <div
        className={cn(
          'mt-2 text-2xl font-semibold tabular-nums',
          accent === 'pos' ? 'text-success' : accent === 'neg' ? 'text-danger' : 'text-ink',
        )}
      >
        {value}
      </div>
    </div>
  )
}
