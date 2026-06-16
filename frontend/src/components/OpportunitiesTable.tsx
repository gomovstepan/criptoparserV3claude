import type { Opportunity } from '../types'
import { cn } from '../lib/utils'

export default function OpportunitiesTable({ items }: { items: Opportunity[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase text-muted">
            <th className="pb-2 pr-4 font-medium">Pair</th>
            <th className="pb-2 pr-4 font-medium">Buy</th>
            <th className="pb-2 pr-4 font-medium">Sell</th>
            <th className="pb-2 pr-4 text-right font-medium">Gross %</th>
            <th className="pb-2 text-right font-medium">Net %</th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 && (
            <tr>
              <td colSpan={5} className="py-6 text-center text-muted">
                Нет данных
              </td>
            </tr>
          )}
          {items.map((o) => (
            <tr key={o.id} className="border-t border-edge/60">
              <td className="py-2 pr-4 font-mono text-ink">{o.symbol}</td>
              <td className="py-2 pr-4 capitalize text-muted">{o.buy_exchange}</td>
              <td className="py-2 pr-4 capitalize text-muted">{o.sell_exchange}</td>
              <td className="py-2 pr-4 text-right font-mono text-ink">{o.gross_spread_pct.toFixed(3)}</td>
              <td
                className={cn(
                  'py-2 text-right font-mono',
                  o.net_spread_pct >= 0 ? 'text-success' : 'text-danger',
                )}
              >
                {o.net_spread_pct.toFixed(3)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
