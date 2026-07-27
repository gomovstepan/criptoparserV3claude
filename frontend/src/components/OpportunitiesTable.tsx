import { TrendingDown, TrendingUp, Search } from 'lucide-react'
import type { Opportunity } from '../types'
import { cn } from '../lib/utils'
import { formatPct, formatPrice } from '../lib/format'
import { GLOSSARY } from '../lib/glossary'
import { useDashboardStore, priceKey } from '../store/dashboardStore'
import Tooltip from './Tooltip'
import EmptyState from './EmptyState'
import { SkeletonTable } from './LoadingSkeleton'

// Живой цене старше этого — не верим: показываем цену момента обнаружения.
const PRICE_STALE_MS = 15_000

/** Имя биржи + живая цена под ним (ask для buy-стороны, bid для sell-стороны). */
function ExchangeCell({
  exchange,
  symbol,
  side,
  detectedPrice,
}: {
  exchange: string
  symbol: string
  side: 'buy' | 'sell'
  detectedPrice: number
}) {
  const live = useDashboardStore((s) => s.prices[priceKey(exchange, symbol)])
  const fresh = live !== undefined && Date.now() - live.ts < PRICE_STALE_MS
  const price = fresh ? (side === 'buy' ? live.ask : live.bid) : detectedPrice
  const label = side === 'buy' ? 'ask' : 'bid'
  return (
    <td className="py-2 pr-4 align-top">
      <div className="capitalize text-muted">{exchange}</div>
      <div
        className={cn('font-mono text-xs tabular-nums', fresh ? 'text-ink' : 'text-muted/70')}
        title={
          fresh
            ? `Текущий ${label} на ${exchange} (обновляется раз в секунду)`
            : `Цена на момент обнаружения спреда — свежих тиков с ${exchange} нет`
        }
      >
        {formatPrice(price)}
      </div>
    </td>
  )
}

export default function OpportunitiesTable({
  items,
  loading = false,
}: {
  items: Opportunity[]
  loading?: boolean
}) {
  if (loading) return <SkeletonTable rows={6} cols={5} />

  if (items.length === 0) {
    return (
      <EmptyState
        icon={Search}
        title="Спредов не найдено"
        hint="Сканер публикует спред, только когда он выше порога min_spread_pct и стакан достаточно глубокий."
      />
    )
  }

  return (
    <div className="relative overflow-x-auto">
      <table className="w-full text-sm" aria-label="Арбитражные спреды">
        <thead>
          <tr className="text-left text-xs uppercase text-muted">
            <th scope="col" className="pb-2 pr-4 font-medium">
              <Tooltip text={GLOSSARY['Pair']}>Pair</Tooltip>
            </th>
            <th scope="col" className="pb-2 pr-4 font-medium">
              <Tooltip text={GLOSSARY['Buy']}>Buy</Tooltip>
            </th>
            <th scope="col" className="pb-2 pr-4 font-medium">
              <Tooltip text={GLOSSARY['Sell']}>Sell</Tooltip>
            </th>
            <th scope="col" className="pb-2 pr-4 text-right font-medium">
              <Tooltip text={GLOSSARY['Gross %']}>Gross %</Tooltip>
            </th>
            <th scope="col" className="pb-2 text-right font-medium">
              <Tooltip text={GLOSSARY['Net %']}>Net %</Tooltip>
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((o) => {
            // Честный net (gross − taker-комиссии); net_spread_pct — только
            // fallback для старых записей без комиссий в payload.
            const net = o.net_fees_pct ?? o.net_spread_pct
            const positive = net >= 0
            const Arrow = positive ? TrendingUp : TrendingDown
            return (
              <tr key={o.id} className="border-t border-edge/60">
                <td className="py-2 pr-4 align-top font-mono text-ink">{o.symbol}</td>
                <ExchangeCell
                  exchange={o.buy_exchange}
                  symbol={o.symbol}
                  side="buy"
                  detectedPrice={o.buy_price}
                />
                <ExchangeCell
                  exchange={o.sell_exchange}
                  symbol={o.symbol}
                  side="sell"
                  detectedPrice={o.sell_price}
                />
                <td className="py-2 pr-4 text-right align-top font-mono text-ink">
                  {formatPct(o.gross_spread_pct, 3)}
                </td>
                {/* Знак и стрелка, а не только цвет: правило color-not-only */}
                <td
                  className={cn(
                    'py-2 text-right align-top font-mono',
                    positive ? 'text-success' : 'text-danger',
                  )}
                >
                  <span className="inline-flex items-center justify-end gap-1">
                    <Arrow size={13} aria-hidden="true" />
                    {formatPct(net, 3, true)}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
