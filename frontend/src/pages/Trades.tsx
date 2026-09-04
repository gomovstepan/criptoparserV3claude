import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Trash2 } from 'lucide-react'
import { useTradeStore, hasActiveFilters } from '../store/tradeStore'
import { EXCHANGE_LIST, SYMBOLS, TRADE_STATUSES } from '../types'
import Panel from '../components/Panel'
import Select from '../components/Select'
import TradeTable from '../components/TradeTable'
import TradeDetailDrawer from '../components/TradeDetailDrawer'
import Pagination from '../components/Pagination'
import ExportCSV from '../components/ExportCSV'
import Modal from '../components/Modal'

export default function Trades() {
  const {
    items, total, page, pageSize, totalPages, loading, filters, selected,
    setFilter, setPage, setPageSize, select, fetch, deleteFiltered,
  } = useTradeStore()

  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const filtered = hasActiveFilters(filters)

  useEffect(() => {
    fetch()
  }, [page, pageSize, filters, fetch])

  const onConfirmDelete = async () => {
    setDeleting(true)
    try {
      const r = await deleteFiltered()
      if (r.truncated) {
        toast.success(`История очищена (${r.deleted.toLocaleString()})`)
      } else {
        toast.success(`Удалено сделок: ${r.deleted.toLocaleString()}`)
      }
      setConfirmOpen(false)
    } catch {
      toast.error('Не удалось удалить сделки')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-ink">Trades</h1>

      <Panel title="Фильтры">
        <div className="flex flex-wrap items-end gap-4">
          <Select label="Статус" value={filters.status} onChange={(v) => setFilter('status', v)} options={TRADE_STATUSES} />
          <Select label="Пара" value={filters.symbol} onChange={(v) => setFilter('symbol', v)} options={SYMBOLS} />
          <Select label="Биржа" value={filters.exchange} onChange={(v) => setFilter('exchange', v)} options={EXCHANGE_LIST} />
          <label className="flex flex-col gap-1 text-xs text-muted">
            С даты
            <input
              type="date"
              value={filters.start}
              onChange={(e) => setFilter('start', e.target.value)}
              className="rounded-lg border border-edge bg-surface2 px-3 py-2 text-sm text-ink outline-none focus:border-accent"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted">
            По дату
            <input
              type="date"
              value={filters.end}
              onChange={(e) => setFilter('end', e.target.value)}
              className="rounded-lg border border-edge bg-surface2 px-3 py-2 text-sm text-ink outline-none focus:border-accent"
            />
          </label>
          <ExportCSV filters={filters} />
          <button
            onClick={() => setConfirmOpen(true)}
            disabled={total === 0}
            className="flex items-center gap-2 self-end rounded-lg border border-danger/40 bg-surface2 px-3 py-2 text-sm text-danger hover:border-danger disabled:opacity-50"
          >
            <Trash2 size={16} />
            {filtered ? 'Удалить по фильтру' : 'Очистить историю'}
          </button>
        </div>
      </Panel>

      <Panel title={`Сделки (${total.toLocaleString()})`}>
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
            <button
              onClick={() => setConfirmOpen(false)}
              disabled={deleting}
              className="rounded-lg border border-edge bg-surface2 px-3 py-2 text-sm text-ink hover:border-accent disabled:opacity-50"
            >
              Отмена
            </button>
            <button
              onClick={onConfirmDelete}
              disabled={deleting}
              className="rounded-lg border border-danger bg-danger/10 px-3 py-2 text-sm text-danger hover:bg-danger/20 disabled:opacity-50"
            >
              {deleting ? 'Удаление…' : 'Удалить'}
            </button>
          </>
        }
      >
        {filtered ? (
          <p>
            Будут удалены сделки, попадающие под текущие фильтры
            {total > 0 ? ` (${total.toLocaleString()} шт.)` : ''}. Действие нельзя отменить.
          </p>
        ) : (
          <p>
            Будут удалены <b>все</b> сделки в истории
            {total > 0 ? ` (${total.toLocaleString()} шт.)` : ''}. Действие нельзя отменить.
          </p>
        )}
      </Modal>
    </div>
  )
}
