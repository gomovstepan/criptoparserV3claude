import { cn } from '../lib/utils'

const STATUS_STYLES: Record<string, string> = {
  completed: 'bg-success/15 text-success',
  failed: 'bg-danger/15 text-danger',
  pending: 'bg-warning/15 text-warning',
  cancelled: 'bg-muted/15 text-muted',
}

/** Цветной badge статуса сделки. */
export default function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        'inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize',
        STATUS_STYLES[status] ?? 'bg-muted/15 text-muted',
      )}
    >
      {status}
    </span>
  )
}
