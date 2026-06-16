import { useEffect } from 'react'
import { useTradeStore } from '../store/tradeStore'
import { EXCHANGE_LIST, SYMBOLS, TRADE_STATUSES } from '../types'
import Panel from '../components/Panel'
import Select from '../components/Select'
import TradeTable from '../components/TradeTable'
import TradeDetailDrawer from '../components/TradeDetailDrawer'
import Pagination from '../components/Pagination'
import ExportCSV from '../components/ExportCSV'

export default function Trades() {
  const {
    items, total, page, pageSize, totalPages, loading, filters, selected,
    setFilter, setPage, setPageSize, select, fetch,
  } = useTradeStore()

  useEffect(() => {
    fetch()
  }, [page, pageSize, filters, fetch])

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
    </div>
  )
}
