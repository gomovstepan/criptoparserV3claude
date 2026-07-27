import { useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import type { Trade } from '../types'
import { cn } from '../lib/utils'
import { formatAmount, formatDateTime, formatDuration, formatExecPrice, formatUsd } from '../lib/format'
import { useDialog } from '../hooks/useDialog'
import StatusBadge from './StatusBadge'
import Button from './Button'

function Row({ label, value, accent }: { label: string; value: string; accent?: 'pos' | 'neg' }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-edge/50 py-2 text-sm">
      <span className="shrink-0 text-muted">{label}</span>
      <span
        className={cn(
          'break-all text-right font-mono text-ink',
          accent === 'pos' && 'text-success',
          accent === 'neg' && 'text-danger',
        )}
      >
        {value}
      </span>
    </div>
  )
}

/**
 * Боковая панель с подробностями сделки.
 *
 * Раньше панель всегда присутствовала в DOM (её содержимое читал скринридер
 * даже в закрытом виде) и закрывалась только мышью. Теперь монтируется по
 * необходимости и ведёт себя как диалог: Esc, ловушка фокуса, возврат фокуса
 * на строку таблицы, блокировка прокрутки фона.
 */
export default function TradeDetailDrawer({
  trade,
  onClose,
}: {
  trade: Trade | null
  onClose: () => void
}) {
  const panelRef = useRef<HTMLElement>(null)
  const titleId = useId()

  useDialog(trade !== null, onClose, panelRef)

  if (!trade) return null

  return createPortal(
    <div className="fixed inset-0 z-drawer">
      <div
        aria-hidden="true"
        onClick={onClose}
        className="absolute inset-0 animate-[fade-in_var(--t-base)_ease-out] bg-black/50"
      />
      <aside
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="absolute right-0 top-0 flex h-full w-full max-w-md animate-[slide-in-right_var(--t-slow)_ease-out] flex-col overflow-y-auto border-l border-edge bg-surface p-5 shadow-2xl outline-none"
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 id={titleId} className="text-lg font-semibold text-ink">
              Сделка
            </h2>
            <p className="break-all font-mono text-xs text-muted">{trade.id}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Закрыть панель сделки">
            <X size={18} aria-hidden="true" />
          </Button>
        </div>

        <div className="mb-4 flex flex-wrap items-center gap-3">
          <span className="font-mono text-ink">{trade.symbol}</span>
          <StatusBadge status={trade.status} />
        </div>

        <Row label="Время" value={formatDateTime(trade.executed_at)} />
        <Row label="Маршрут" value={`${trade.buy_exchange} → ${trade.sell_exchange}`} />
        {/* Цены исполнения — VWAP прохода по стакану; top-of-book тех же
            стаканов рядом, чтобы объяснить проскальзывание. */}
        {trade.buy_price != null && (
          <Row label="Покупка (VWAP)" value={`$${formatExecPrice(trade.buy_price)}`} />
        )}
        {trade.buy_top_ask != null && (
          <Row label="Покупка (top ask)" value={`$${formatExecPrice(trade.buy_top_ask)}`} />
        )}
        {trade.sell_price != null && (
          <Row label="Продажа (VWAP)" value={`$${formatExecPrice(trade.sell_price)}`} />
        )}
        {trade.sell_top_bid != null && (
          <Row label="Продажа (top bid)" value={`$${formatExecPrice(trade.sell_top_bid)}`} />
        )}
        <Row label="Объём" value={formatAmount(trade.amount)} />

        {/* Разложение: net = gross − slippage − buy_fee − sell_fee */}
        <Row
          label="Gross P&L (по top-of-book)"
          value={formatUsd(trade.gross_pnl, true)}
          accent={trade.gross_pnl >= 0 ? 'pos' : 'neg'}
        />
        {trade.slippage_cost != null && (
          <Row
            label="− Проскальзывание"
            value={formatUsd(-trade.slippage_cost)}
            accent={trade.slippage_cost > 0 ? 'neg' : undefined}
          />
        )}
        {trade.buy_fee != null && (
          <Row label="− Комиссия покупки" value={formatUsd(-trade.buy_fee)} />
        )}
        {trade.sell_fee != null && (
          <Row label="− Комиссия продажи" value={formatUsd(-trade.sell_fee)} />
        )}
        <Row
          label="= Net P&L"
          value={formatUsd(trade.net_pnl, true)}
          accent={trade.net_pnl >= 0 ? 'pos' : 'neg'}
        />
        {trade.duration_ms != null && (
          <Row label="Длительность" value={formatDuration(trade.duration_ms)} />
        )}
        {trade.opportunity_id && <Row label="Opportunity ID" value={trade.opportunity_id} />}

        <p className="mt-4 text-xs text-muted">
          Комиссия за вывод не входит в net P&L сделки — она списывается один раз при
          ребалансировке балансов между биржами.
        </p>
      </aside>
    </div>,
    document.body,
  )
}
