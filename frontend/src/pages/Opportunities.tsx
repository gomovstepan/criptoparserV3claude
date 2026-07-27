import { useCallback, useEffect, useMemo, useState } from 'react'
import { FilterX, ServerCrash } from 'lucide-react'
import api from '../lib/api'
import { useDashboardStore } from '../store/dashboardStore'
import { EXCHANGE_LIST, SYMBOLS } from '../types'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { formatCount } from '../lib/format'
import { asArray, cn } from '../lib/utils'
import OpportunitiesTable from '../components/OpportunitiesTable'
import Panel from '../components/Panel'
import Select from '../components/Select'
import Button from '../components/Button'
import EmptyState from '../components/EmptyState'

type PnlFilter = 'all' | 'positive' | 'negative'

const PNL_FILTERS: { value: PnlFilter; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'positive', label: 'Прибыльные' },
  { value: 'negative', label: 'Убыточные' },
]

export default function Opportunities() {
  useDocumentTitle('Opportunities')

  const opportunities = useDashboardStore((s) => s.opportunities)
  const [symbol, setSymbol] = useState('')
  const [buyEx, setBuyEx] = useState('')
  const [sellEx, setSellEx] = useState('')
  const [pnlFilter, setPnlFilter] = useState<PnlFilter>('all')
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const url = `/api/v1/opportunities?limit=50${symbol ? `&symbol=${encodeURIComponent(symbol)}` : ''}`
      const r = await api.get(url)
      useDashboardStore.getState().setOpportunities(asArray(r.data?.items))
      setFailed(false)
    } catch {
      setFailed(true)
    } finally {
      setLoading(false)
    }
  }, [symbol])

  useEffect(() => {
    load()
  }, [load])

  const filtered = useMemo(
    () =>
      opportunities.filter((o) => {
        // Честный net: gross − taker-комиссии обеих ног. net_spread_pct
        // display-only (завышает комиссию вывода ~40x) — фильтровать по нему
        // нельзя, иначе почти всё помечается «убыточным».
        const net = o.net_fees_pct ?? o.net_spread_pct
        return (
          (!symbol || o.symbol === symbol) &&
          (!buyEx || o.buy_exchange === buyEx) &&
          (!sellEx || o.sell_exchange === sellEx) &&
          (pnlFilter === 'all' || (pnlFilter === 'positive' ? net >= 0 : net < 0))
        )
      }),
    [opportunities, symbol, buyEx, sellEx, pnlFilter],
  )

  const hasFilters = Boolean(symbol || buyEx || sellEx || pnlFilter !== 'all')
  const reset = () => {
    setSymbol('')
    setBuyEx('')
    setSellEx('')
    setPnlFilter('all')
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-ink">Opportunities</h1>

      <Panel title="Фильтры">
        <div className="flex flex-wrap items-end gap-4">
          <Select label="Пара" value={symbol} onChange={setSymbol} options={SYMBOLS} />
          <Select label="Buy биржа" value={buyEx} onChange={setBuyEx} options={EXCHANGE_LIST} />
          <Select label="Sell биржа" value={sellEx} onChange={setSellEx} options={EXCHANGE_LIST} />
          <div
            role="group"
            aria-label="Фильтр по знаку net-спреда"
            className="flex overflow-hidden rounded-lg border border-edge-strong"
          >
            {PNL_FILTERS.map((f) => (
              <button
                key={f.value}
                type="button"
                aria-pressed={pnlFilter === f.value}
                onClick={() => setPnlFilter(f.value)}
                className={cn(
                  'tap-target min-h-[34px] px-3 py-1.5 text-sm font-medium transition-colors duration-fast',
                  pnlFilter === f.value
                    ? 'bg-accent text-on-accent'
                    : 'bg-surface2 text-muted hover:text-ink',
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
          {hasFilters && (
            <Button variant="ghost" onClick={reset}>
              <FilterX size={16} aria-hidden="true" />
              Сбросить
            </Button>
          )}
        </div>
      </Panel>

      <Panel
        title={`Спреды (${formatCount(filtered.length)})`}
        right={<span className="text-xs text-muted">real-time</span>}
      >
        {failed ? (
          <EmptyState
            tone="danger"
            icon={ServerCrash}
            title="Не удалось загрузить спреды"
            hint="Сканер или api-gateway недоступен."
            onRetry={load}
          />
        ) : (
          <OpportunitiesTable items={filtered} loading={loading && opportunities.length === 0} />
        )}
      </Panel>
    </div>
  )
}
