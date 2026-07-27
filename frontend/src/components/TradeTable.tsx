import { ChevronRight, Inbox } from 'lucide-react'
import type { Trade } from '../types'
import { cn } from '../lib/utils'
import { formatAmount, formatDateTime, formatUsd } from '../lib/format'
import { GLOSSARY } from '../lib/glossary'
import StatusBadge from './StatusBadge'
import Tooltip from './Tooltip'
import EmptyState from './EmptyState'
import { SkeletonTable } from './LoadingSkeleton'

/**
 * Таблица paper trades.
 *
 * Строка по-прежнему открывает подробности по клику мышью, но действие
 * продублировано настоящей кнопкой в последней колонке: клик по `<tr>` не
 * достижим ни с клавиатуры, ни скринридером (правило keyboard-nav).
 */
export default function TradeTable({
  items,
  loading,
  onRowClick,
}: {
  items: Trade[]
  loading?: boolean
  onRowClick: (t: Trade) => void
}) {
  if (loading) return <SkeletonTable rows={8} cols={6} />

  if (items.length === 0) {
    return (
      <EmptyState
        icon={Inbox}
        title="Сделок не найдено"
        hint="Попробуйте снять фильтры или расширить период — история хранится в TimescaleDB."
      />
    )
  }

  return (
    <div className="relative overflow-x-auto">
      <table className="w-full text-sm" aria-label="История сделок">
        <thead>
          <tr className="text-left text-xs uppercase text-muted">
            <th scope="col" className="pb-2 pr-4 font-medium">
              <Tooltip text={GLOSSARY['Time']}>Time</Tooltip>
            </th>
            <th scope="col" className="pb-2 pr-4 font-medium">
              <Tooltip text={GLOSSARY['Pair']}>Pair</Tooltip>
            </th>
            <th scope="col" className="pb-2 pr-4 font-medium">
              <Tooltip text={GLOSSARY['Route']}>Route</Tooltip>
            </th>
            <th scope="col" className="pb-2 pr-4 text-right font-medium">
              <Tooltip text={GLOSSARY['Amount']}>Amount</Tooltip>
            </th>
            <th scope="col" className="pb-2 pr-4 text-right font-medium">
              <Tooltip text={GLOSSARY['Gross P&L']}>Gross P&amp;L</Tooltip>
            </th>
            <th scope="col" className="pb-2 pr-4 text-right font-medium">
              <Tooltip text={GLOSSARY['Net P&L']}>Net P&amp;L</Tooltip>
            </th>
            <th scope="col" className="pb-2 pr-4 font-medium">
              <Tooltip text={GLOSSARY['Status']}>Status</Tooltip>
            </th>
            {/* Пустой заголовок с именем через aria-label. Через <span class="sr-only">
                нельзя: это position:absolute без позиционированного предка, поэтому
                элемент выпадал из обрезающего контейнера и растягивал страницу
                по горизонтали на 265px при 375px ширины. */}
            <th scope="col" aria-label="Подробности" className="pb-2" />
          </tr>
        </thead>
        <tbody>
          {items.map((t) => (
            <tr
              key={t.id}
              onClick={() => onRowClick(t)}
              className="cursor-pointer border-t border-edge/60 transition-colors duration-fast hover:bg-surface2"
            >
              <td className="py-2 pr-4 text-xs text-muted">{formatDateTime(t.executed_at)}</td>
              <td className="py-2 pr-4 font-mono text-ink">{t.symbol}</td>
              <td className="py-2 pr-4 text-xs capitalize text-muted">
                {t.buy_exchange} → {t.sell_exchange}
              </td>
              <td className="py-2 pr-4 text-right font-mono text-muted">{formatAmount(t.amount)}</td>
              <td
                className={cn(
                  'py-2 pr-4 text-right font-mono',
                  t.gross_pnl >= 0 ? 'text-success' : 'text-danger',
                )}
              >
                {formatUsd(t.gross_pnl, true)}
              </td>
              <td
                className={cn(
                  'py-2 pr-4 text-right font-mono',
                  t.net_pnl >= 0 ? 'text-success' : 'text-danger',
                )}
              >
                {formatUsd(t.net_pnl, true)}
              </td>
              <td className="py-2 pr-4">
                <StatusBadge status={t.status} />
              </td>
              <td className="py-2 text-right">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    onRowClick(t)
                  }}
                  aria-label={`Подробности сделки ${t.symbol} от ${formatDateTime(t.executed_at)}`}
                  // Без .tap-target: строки таблицы низкие, расширенная зона
                  // залезала бы на соседнюю строку. Для мыши и тача целью
                  // остаётся вся строка, кнопка нужна клавиатуре и скринридеру.
                  className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-muted transition-colors duration-fast hover:bg-surface hover:text-ink"
                >
                  <ChevronRight size={16} aria-hidden="true" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
