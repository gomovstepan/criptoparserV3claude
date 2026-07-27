import { Wifi, WifiOff } from 'lucide-react'
import { cn } from '../lib/utils'

/**
 * Плитка статуса биржи.
 * Состояние передаётся иконкой + подписью, а не только цветом точки.
 */
export default function ExchangeStatusCard({
  exchange,
  online,
  latencyMs,
}: {
  exchange: string
  online: boolean
  latencyMs: number | null
}) {
  const Icon = online ? Wifi : WifiOff
  return (
    <div className="rounded-lg border border-edge bg-surface2 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-sm font-medium capitalize text-ink">{exchange}</span>
        <Icon
          size={14}
          aria-hidden="true"
          className={cn('shrink-0', online ? 'text-success' : 'text-danger')}
        />
      </div>
      <div className={cn('mt-1 text-xs tabular-nums', online ? 'text-muted' : 'text-danger')}>
        {online ? (latencyMs != null ? `${latencyMs} ms` : 'онлайн') : 'офлайн'}
      </div>
    </div>
  )
}
