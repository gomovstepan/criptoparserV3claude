import { cn } from '../lib/utils'

export default function ExchangeStatusCard({
  exchange,
  online,
  latencyMs,
}: {
  exchange: string
  online: boolean
  latencyMs: number | null
}) {
  return (
    <div className="rounded-lg border border-edge bg-surface2 p-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium capitalize text-ink">{exchange}</span>
        <span
          className={cn(
            'h-2 w-2 rounded-full',
            online ? 'bg-success shadow-[0_0_6px] shadow-success' : 'bg-danger',
          )}
        />
      </div>
      <div className="mt-1 text-xs text-muted">
        {online ? (latencyMs != null ? `${latencyMs} ms` : 'online') : 'offline'}
      </div>
    </div>
  )
}
