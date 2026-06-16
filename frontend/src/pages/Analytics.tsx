import { useEffect, useState } from 'react'
import { Activity, Award, Percent, TrendingDown, TrendingUp, Wallet } from 'lucide-react'
import api from '../lib/api'
import type { AnalyticsSummary } from '../types'
import KPICard from '../components/KPICard'
import Panel from '../components/Panel'
import DateRangePicker from '../components/DateRangePicker'
import CumulativePnLChart from '../components/CumulativePnLChart'
import DailyPnLChart from '../components/DailyPnLChart'
import TradesPerDayChart from '../components/TradesPerDayChart'

export default function Analytics() {
  const [days, setDays] = useState(7)
  const [data, setData] = useState<AnalyticsSummary | null>(null)

  useEffect(() => {
    api
      .get(`/api/v1/analytics/pnl?days=${days}`)
      .then((r) => setData(r.data))
      .catch(() => setData(null))
  }, [days])

  const daily = data?.daily ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-ink">Analytics</h1>
        <DateRangePicker days={days} onChange={setDays} />
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
        <KPICard title="Total Trades" value={data ? data.total_trades.toLocaleString() : '…'} icon={Activity} />
        <KPICard title="Win Rate" value={data ? `${data.win_rate.toFixed(1)}%` : '…'} icon={Percent} />
        <KPICard
          title="Net P&L"
          value={data ? `$${data.total_net_pnl.toFixed(2)}` : '…'}
          icon={Wallet}
          accent={data ? (data.total_net_pnl >= 0 ? 'pos' : 'neg') : 'default'}
        />
        <KPICard
          title="Gross P&L"
          value={data ? `$${data.total_gross_pnl.toFixed(2)}` : '…'}
          icon={TrendingUp}
          accent={data ? (data.total_gross_pnl >= 0 ? 'pos' : 'neg') : 'default'}
        />
        <KPICard title="Best Trade" value={data ? `$${data.best_trade.toFixed(2)}` : '…'} icon={Award} accent="pos" />
        <KPICard title="Worst Trade" value={data ? `$${data.worst_trade.toFixed(2)}` : '…'} icon={TrendingDown} accent="neg" />
      </div>

      <Panel title="Cumulative net P&L">
        <CumulativePnLChart data={daily} />
      </Panel>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel title="Net P&L по дням">
          <DailyPnLChart data={daily} />
        </Panel>
        <Panel title="Сделок по дням">
          <TradesPerDayChart data={daily} />
        </Panel>
      </div>
    </div>
  )
}
