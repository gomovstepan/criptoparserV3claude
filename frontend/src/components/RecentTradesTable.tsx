import type { Trade } from '../types'
import { cn } from '../lib/utils'
import { GLOSSARY } from '../lib/glossary'
import Tooltip from './Tooltip'

export default function RecentTradesTable({ items }: { items: Trade[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase text-muted">
            <th className="pb-2 pr-4 font-medium"><Tooltip text={GLOSSARY['Pair']}>Pair</Tooltip></th>
            <th className="pb-2 pr-4 font-medium"><Tooltip text={GLOSSARY['Route']}>Route</Tooltip></th>
            <th className="pb-2 text-right font-medium"><Tooltip text={GLOSSARY['Net P&L']}>Net P&amp;L</Tooltip></th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 && (
            <tr>
              <td colSpan={3} className="py-6 text-center text-muted">
                Нет сделок
              </td>
            </tr>
          )}
          {items.map((t) => (
            <tr key={t.id} className="border-t border-edge/60">
              <td className="py-2 pr-4 font-mono text-ink">{t.symbol}</td>
              <td className="py-2 pr-4 text-xs capitalize text-muted">
                {t.buy_exchange}→{t.sell_exchange}
              </td>
              <td
                className={cn(
                  'py-2 text-right font-mono',
                  t.net_pnl >= 0 ? 'text-success' : 'text-danger',
                )}
              >
                ${t.net_pnl.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
