import type { LucideIcon } from 'lucide-react'
import { cn } from '../lib/utils'

export default function KPICard({
  title,
  value,
  icon: Icon,
  accent = 'default',
}: {
  title: string
  value: string
  icon: LucideIcon
  accent?: 'pos' | 'neg' | 'default'
}) {
  return (
    <div className="rounded-xl border border-edge bg-surface p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-muted">{title}</span>
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
