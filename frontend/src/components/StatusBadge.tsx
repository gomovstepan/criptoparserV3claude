import { Ban, CheckCircle2, Clock, XCircle, type LucideIcon } from 'lucide-react'
import { cn } from '../lib/utils'

/**
 * Badge статуса сделки.
 * К цвету добавлены иконка и русская подпись: смысл не должен передаваться
 * одним лишь цветом (правило color-not-only — критично для дальтоников,
 * а красный/зелёный здесь основная пара).
 */
const STATUS: Record<string, { className: string; label: string; icon: LucideIcon }> = {
  completed: { className: 'bg-success/15 text-success', label: 'Исполнена', icon: CheckCircle2 },
  failed: { className: 'bg-danger/15 text-danger', label: 'Ошибка', icon: XCircle },
  pending: { className: 'bg-warning/15 text-warning', label: 'В процессе', icon: Clock },
  cancelled: { className: 'bg-muted/15 text-muted', label: 'Отменена', icon: Ban },
}

export default function StatusBadge({ status }: { status: string }) {
  const meta = STATUS[status]
  const Icon = meta?.icon ?? Ban
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium',
        meta?.className ?? 'bg-muted/15 text-muted',
      )}
      title={status}
    >
      <Icon size={12} aria-hidden="true" />
      {meta?.label ?? status}
    </span>
  )
}
