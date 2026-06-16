import type { Trade } from '../types'
import { cn } from '../lib/utils'
import StatusBadge from './StatusBadge'

function fmtTime(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString()
}

/** Таблица paper trades. Клик по строке открывает detail drawer. */
export default function TradeTable({
  items,
  loading,
  onRowClick,
}: {
  items: Trade[]
  loading?: boolean
  onRowClick: (t: Trade) => void
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase text-muted">
            <th className="pb-2 pr-4 font-medium">Time</th>
            <th className="pb-2 pr-4 font-medium">Pair</th>
            <th className="pb-2 pr-4 font-medium">Route</th>
            <th className="pb-2 pr-4 text-right font-medium">Amount</th>
            <th className="pb-2 pr-4 text-right font-medium">Gross P&amp;L</th>
            <th className="pb-2 pr-4 text-right font-medium">Net P&amp;L</th>
            <th className="pb-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {loading && (
            <tr>
              <td colSpan={7} className="py-6 text-center text-muted">
                Загрузка…
              </td>
            </tr>
          )}
          {!loading && items.length === 0 && (
            <tr>
              <td colSpan={7} className="py-6 text-center text-muted">
                Сделок не найдено
              </td>
            </tr>
          )}
          {!loading &&
            items.map((t) => (
              <tr
                key={t.id}
                onClick={() => onRowClick(t)}
                className="cursor-pointer border-t border-edge/60 transition-colors hover:bg-surface2"
              >
                <td className="py-2 pr-4 text-xs text-muted">{fmtTime(t.executed_at)}</td>
                <td className="py-2 pr-4 font-mono text-ink">{t.symbol}</td>
                <td className="py-2 pr-4 text-xs capitalize text-muted">
                  {t.buy_exchange}→{t.sell_exchange}
                </td>
                <td className="py-2 pr-4 text-right font-mono text-muted">{t.amount.toFixed(6)}</td>
                <td
                  className={cn(
                    'py-2 pr-4 text-right font-mono',
                    t.gross_pnl >= 0 ? 'text-success' : 'text-danger',
                  )}
                >
                  ${t.gross_pnl.toFixed(2)}
                </td>
                <td
                  className={cn(
                    'py-2 pr-4 text-right font-mono',
                    t.net_pnl >= 0 ? 'text-success' : 'text-danger',
                  )}
                >
                  ${t.net_pnl.toFixed(2)}
                </td>
                <td className="py-2">
                  <StatusBadge status={t.status} />
                </td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  )
}
