import { useEffect, useMemo, useState } from 'react'
import api from '../lib/api'
import { useDashboardStore } from '../store/dashboardStore'
import { EXCHANGE_LIST, SYMBOLS } from '../types'
import OpportunitiesTable from '../components/OpportunitiesTable'
import Panel from '../components/Panel'
import Select from '../components/Select'

export default function Opportunities() {
  const opportunities = useDashboardStore((s) => s.opportunities)
  const [symbol, setSymbol] = useState('')
  const [buyEx, setBuyEx] = useState('')
  const [sellEx, setSellEx] = useState('')

  useEffect(() => {
    const url = `/api/v1/opportunities?limit=50${symbol ? `&symbol=${encodeURIComponent(symbol)}` : ''}`
    api
      .get(url)
      .then((r) => useDashboardStore.getState().setOpportunities(r.data.items))
      .catch(() => undefined)
  }, [symbol])

  const filtered = useMemo(
    () =>
      opportunities.filter(
        (o) =>
          (!symbol || o.symbol === symbol) &&
          (!buyEx || o.buy_exchange === buyEx) &&
          (!sellEx || o.sell_exchange === sellEx),
      ),
    [opportunities, symbol, buyEx, sellEx],
  )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-ink">Opportunities</h1>

      <Panel title="Фильтры">
        <div className="flex flex-wrap gap-4">
          <Select label="Пара" value={symbol} onChange={setSymbol} options={SYMBOLS} />
          <Select label="Buy биржа" value={buyEx} onChange={setBuyEx} options={EXCHANGE_LIST} />
          <Select label="Sell биржа" value={sellEx} onChange={setSellEx} options={EXCHANGE_LIST} />
        </div>
      </Panel>

      <Panel
        title={`Спреды (${filtered.length})`}
        right={<span className="text-xs text-muted">real-time</span>}
      >
        <OpportunitiesTable items={filtered} />
      </Panel>
    </div>
  )
}
