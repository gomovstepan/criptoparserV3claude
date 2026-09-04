import { X } from 'lucide-react'
import type { Trade } from '../types'
import { cn } from '../lib/utils'
import { formatPrice } from '../lib/format'
import StatusBadge from './StatusBadge'

function Row({ label, value, accent }: { label: string; value: string; accent?: 'pos' | 'neg' }) {
  return (
    <div className="flex items-center justify-between border-b border-edge/50 py-2 text-sm">
      <span className="text-muted">{label}</span>
      <span
        className={cn(
          'font-mono text-ink',
          accent === 'pos' && 'text-success',
          accent === 'neg' && 'text-danger',
        )}
      >
        {value}
      </span>
    </div>
  )
}

/** Боковая панель с подробностями сделки. */
export default function TradeDetailDrawer({ trade, onClose }: { trade: Trade | null; onClose: () => void }) {
  const open = trade !== null
  return (
    <div className={cn('fixed inset-0 z-40', open ? 'pointer-events-auto' : 'pointer-events-none')}>
      {/* затемнение */}
      <div
        onClick={onClose}
        className={cn(
          'absolute inset-0 bg-black/50 transition-opacity',
          open ? 'opacity-100' : 'opacity-0',
        )}
      />
      {/* панель */}
      <aside
        className={cn(
          'absolute right-0 top-0 h-full w-full max-w-md overflow-y-auto border-l border-edge bg-surface p-5 shadow-xl transition-transform',
          open ? 'translate-x-0' : 'translate-x-full',
        )}
      >
        {trade && (
          <>
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold text-ink">Сделка</h2>
                <p className="font-mono text-xs text-muted">{trade.id}</p>
              </div>
              <button
                onClick={onClose}
                className="rounded-lg p-1 text-muted hover:bg-surface2 hover:text-ink"
                aria-label="Закрыть"
              >
                <X size={18} />
              </button>
            </div>

            <div className="mb-4 flex items-center gap-3">
              <span className="font-mono text-ink">{trade.symbol}</span>
              <StatusBadge status={trade.status} />
            </div>

            <Row label="Время" value={new Date(trade.executed_at).toLocaleString()} />
            <Row label="Маршрут" value={`${trade.buy_exchange} → ${trade.sell_exchange}`} />
            {trade.buy_price != null && <Row label="Цена покупки" value={`$${formatPrice(trade.buy_price)}`} />}
            {trade.sell_price != null && <Row label="Цена продажи" value={`$${formatPrice(trade.sell_price)}`} />}
            <Row label="Объём" value={trade.amount.toFixed(6)} />
            <Row label="Gross P&L" value={`$${trade.gross_pnl.toFixed(2)}`} accent={trade.gross_pnl >= 0 ? 'pos' : 'neg'} />
            <Row label="Net P&L" value={`$${trade.net_pnl.toFixed(2)}`} accent={trade.net_pnl >= 0 ? 'pos' : 'neg'} />
            {trade.duration_ms != null && <Row label="Длительность" value={`${trade.duration_ms} ms`} />}
            {trade.opportunity_id && <Row label="Opportunity ID" value={trade.opportunity_id} />}
          </>
        )}
      </aside>
    </div>
  )
}
