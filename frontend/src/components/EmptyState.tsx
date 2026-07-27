import type { LucideIcon } from 'lucide-react'
import { Inbox, RotateCcw } from 'lucide-react'
import Button from './Button'

/**
 * Пустое/ошибочное состояние с подсказкой и, при необходимости, действием.
 *
 * Раньше на месте отсутствующих данных был просто серый текст «Нет данных»
 * без объяснения причины, а при ошибке загрузки — вечное «…» без возможности
 * повторить запрос (правила empty-states / error-recovery / error-state-chart).
 */
export default function EmptyState({
  icon: Icon = Inbox,
  title,
  hint,
  onRetry,
  retryLabel = 'Повторить',
  tone = 'muted',
  compact = false,
}: {
  icon?: LucideIcon
  title: string
  hint?: string
  onRetry?: () => void
  retryLabel?: string
  tone?: 'muted' | 'danger'
  compact?: boolean
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-2 text-center ${compact ? 'py-6' : 'py-10'}`}
      role={tone === 'danger' ? 'alert' : undefined}
    >
      <span
        className={`flex h-10 w-10 items-center justify-center rounded-full ${
          tone === 'danger' ? 'bg-danger/15 text-danger' : 'bg-surface2 text-muted'
        }`}
      >
        <Icon size={18} aria-hidden="true" />
      </span>
      <p className={`text-sm font-medium ${tone === 'danger' ? 'text-danger' : 'text-ink'}`}>{title}</p>
      {hint && <p className="max-w-sm text-xs text-muted">{hint}</p>}
      {onRetry && (
        <Button size="sm" onClick={onRetry} className="mt-1">
          <RotateCcw size={14} aria-hidden="true" />
          {retryLabel}
        </Button>
      )}
    </div>
  )
}
