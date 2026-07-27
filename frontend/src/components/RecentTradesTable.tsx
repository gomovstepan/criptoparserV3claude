import { ArrowLeftRight } from 'lucide-react'
import type { Trade } from '../types'
import { cn } from '../lib/utils'
import { formatUsd } from '../lib/format'
import { GLOSSARY } from '../lib/glossary'
import Tooltip from './Tooltip'
import EmptyState from './EmptyState'
import { SkeletonTable } from './LoadingSkeleton'

export default function RecentTradesTable({
  items,
  loading = false,
}: {
  items: Trade[]
  loading?: boolean
}) {
  if (loading) return <SkeletonTable rows={6} cols={3} />

  if (items.length === 0) {
    return (
      <EmptyState
        icon={ArrowLeftRight}
        title="Сделок пока нет"
        hint="Executor создаёт сделку, только если стакан подтверждает спред в момент исполнения."
      />
    )
  }

  return (
    <div className="relative overflow-x-auto">
      <table className="w-full text-sm" aria-label="Последние сделки">
        <thead>
          <tr className="text-left text-xs uppercase text-muted">
            <th scope="col" className="pb-2 pr-4 font-medium">
              <Tooltip text={GLOSSARY['Pair']}>Pair</Tooltip>
            </th>
            <th scope="col" className="pb-2 pr-4 font-medium">
              <Tooltip text={GLOSSARY['Route']}>Route</Tooltip>
            </th>
            <th scope="col" className="pb-2 text-right font-medium">
              <Tooltip text={GLOSSARY['Net P&L']}>Net P&amp;L</Tooltip>
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((t) => (
            <tr key={t.id} className="border-t border-edge/60">
              <td className="py-2 pr-4 font-mono text-ink">{t.symbol}</td>
              <td className="py-2 pr-4 text-xs capitalize text-muted">
                {t.buy_exchange} → {t.sell_exchange}
              </td>
              <td
                className={cn(
                  'py-2 text-right font-mono',
                  t.net_pnl >= 0 ? 'text-success' : 'text-danger',
                )}
              >
                {formatUsd(t.net_pnl, true)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
