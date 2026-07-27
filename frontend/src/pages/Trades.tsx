import { useEffect, useId, useRef, useState } from 'react'
import { toast } from 'sonner'
import { AlertTriangle, FilterX, Trash2 } from 'lucide-react'
import { useTradeStore, hasActiveFilters } from '../store/tradeStore'
import { EXCHANGE_LIST, SYMBOLS, TRADE_STATUSES } from '../types'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { formatCount } from '../lib/format'
import Panel from '../components/Panel'
import Select from '../components/Select'
import Button from '../components/Button'
import TradeTable from '../components/TradeTable'
import TradeDetailDrawer from '../components/TradeDetailDrawer'
import Pagination from '../components/Pagination'
import ExportCSV from '../components/ExportCSV'
import Modal from '../components/Modal'

const DATE_DEBOUNCE_MS = 400

export default function Trades() {
  useDocumentTitle('Trades')

  const {
    items, total, page, pageSize, totalPages, loading, filters, selected,
    setFilter, resetFilters, setPage, setPageSize, select, fetch, deleteFiltered,
  } = useTradeStore()

  const startId = useId()
  const endId = useId()
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const filtered = hasActiveFilters(filters)

  // Даты вводятся посимвольно — без задержки каждый символ уходил в новый запрос
  // к /trades (правило debounce-throttle). Поля живут в локальном состоянии,
  // в стор значение уезжает через паузу; таймеры чистятся при размонтировании.
  const [dates, setDates] = useState({ start: filters.start, end: filters.end })
  const timers = useRef<{ start?: number; end?: number }>({})

  useEffect(
    () => () => {
      window.clearTimeout(timers.current.start)
      window.clearTimeout(timers.current.end)
    },
    [],
  )

  const commitDate = (key: 'start' | 'end', value: string) => {
    setDates((p) => ({ ...p, [key]: value }))
    window.clearTimeout(timers.current[key])
    timers.current[key] = window.setTimeout(() => setFilter(key, value), DATE_DEBOUNCE_MS)
  }

  const resetAll = () => {
    window.clearTimeout(timers.current.start)
    window.clearTimeout(timers.current.end)
    setDates({ start: '', end: '' })
    resetFilters()
  }

  useEffect(() => {
    fetch()
  }, [page, pageSize, filters, fetch])

  const onConfirmDelete = async () => {
    setDeleting(true)
    try {
      const r = await deleteFiltered()
      toast.success(
        r.truncated
          ? `История очищена (${formatCount(r.deleted)})`
          : `Удалено сделок: ${formatCount(r.deleted)}`,
      )
      setConfirmOpen(false)
    } catch {
      toast.error('Не удалось удалить сделки')
    } finally {
      setDeleting(false)
    }
  }

  const dateInputClass =
    'min-h-[44px] rounded-lg border border-edge-strong bg-surface2 px-3 py-2 text-sm text-ink transition-colors duration-fast hover:border-accent'

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-ink">Trades</h1>

      <Panel title="Фильтры">
        <div className="flex flex-wrap items-end gap-4">
          <Select label="Статус" value={filters.status} onChange={(v) => setFilter('status', v)} options={TRADE_STATUSES} />
          <Select label="Пара" value={filters.symbol} onChange={(v) => setFilter('symbol', v)} options={SYMBOLS} />
          <Select label="Биржа" value={filters.exchange} onChange={(v) => setFilter('exchange', v)} options={EXCHANGE_LIST} />
          <div className="flex flex-col gap-1">
            <label htmlFor={startId} className="text-xs font-medium text-muted">
              С даты
            </label>
            <input
              id={startId}
              type="date"
              max={dates.end || undefined}
              value={dates.start}
              onChange={(e) => commitDate('start', e.target.value)}
              className={dateInputClass}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor={endId} className="text-xs font-medium text-muted">
              По дату
            </label>
            <input
              id={endId}
              type="date"
              min={dates.start || undefined}
              value={dates.end}
              onChange={(e) => commitDate('end', e.target.value)}
              className={dateInputClass}
            />
          </div>
          {filtered && (
            <Button variant="ghost" onClick={resetAll}>
              <FilterX size={16} aria-hidden="true" />
              Сбросить
            </Button>
          )}
        </div>

        {/* Опасное действие вынесено из ряда фильтров и отделено линией:
            рядом с Export его было слишком легко нажать (destructive-emphasis). */}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-edge pt-4">
          <ExportCSV filters={filters} />
          <Button variant="dangerOutline" onClick={() => setConfirmOpen(true)} disabled={total === 0}>
            <Trash2 size={16} aria-hidden="true" />
            {filtered ? 'Удалить по фильтру' : 'Очистить историю'}
          </Button>
        </div>
      </Panel>

      <Panel title={`Сделки (${formatCount(total)})`}>
        <TradeTable items={items} loading={loading} onRowClick={select} />
        <Pagination
          page={page}
          totalPages={totalPages}
          total={total}
          pageSize={pageSize}
          onPage={setPage}
          onPageSize={setPageSize}
        />
      </Panel>

      <TradeDetailDrawer trade={selected} onClose={() => select(null)} />

      <Modal
        open={confirmOpen}
        title={filtered ? 'Удалить сделки по фильтру?' : 'Очистить всю историю сделок?'}
        onClose={() => !deleting && setConfirmOpen(false)}
        footer={
          <>
            <Button onClick={() => setConfirmOpen(false)} disabled={deleting}>
              Отмена
            </Button>
            <Button variant="danger" onClick={onConfirmDelete} loading={deleting} loadingText="Удаление…">
              Удалить
            </Button>
          </>
        }
      >
        <div className="flex gap-3">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-danger" aria-hidden="true" />
          {filtered ? (
            <p>
              Будут удалены сделки, попадающие под текущие фильтры
              {total > 0 ? ` (${formatCount(total)} шт.)` : ''}. Действие нельзя отменить.
            </p>
          ) : (
            <p>
              Будут удалены <b>все</b> сделки в истории
              {total > 0 ? ` (${formatCount(total)} шт.)` : ''}. Действие нельзя отменить.
            </p>
          )}
        </div>
      </Modal>
    </div>
  )
}
