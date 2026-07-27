import { useCallback, useEffect, useState } from 'react'
import { Activity, Award, Percent, ServerCrash, TrendingDown, TrendingUp, Wallet } from 'lucide-react'
import api from '../lib/api'
import type { AnalyticsSummary, DailyPoint } from '../types'
import { asArray } from '../lib/utils'
import { GLOSSARY } from '../lib/glossary'
import { formatCount, formatDuration, formatPct, formatUsd } from '../lib/format'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import KPICard from '../components/KPICard'
import Panel from '../components/Panel'
import DateRangePicker from '../components/DateRangePicker'
import CumulativePnLChart from '../components/CumulativePnLChart'
import DailyPnLChart from '../components/DailyPnLChart'
import TradesPerDayChart from '../components/TradesPerDayChart'
import EmptyState from '../components/EmptyState'
import { Skeleton, SkeletonCards } from '../components/LoadingSkeleton'

export default function Analytics() {
  useDocumentTitle('Analytics')

  const [days, setDays] = useState(7)
  const [data, setData] = useState<AnalyticsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.get(`/api/v1/analytics/pnl?days=${days}`)
      setData(r.data)
      setFailed(false)
    } catch {
      // Раньше здесь молча выставлялся null: карточки навсегда застревали на «…»
      setData(null)
      setFailed(true)
    } finally {
      setLoading(false)
    }
  }, [days])

  useEffect(() => {
    load()
  }, [load])

  const daily = asArray<DailyPoint>(data?.daily)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-ink">Analytics</h1>
        <DateRangePicker days={days} onChange={setDays} />
      </div>

      {failed ? (
        <div className="rounded-xl border border-edge bg-surface p-4">
          <EmptyState
            tone="danger"
            icon={ServerCrash}
            title="Не удалось загрузить аналитику"
            hint="Запрос к /api/v1/analytics/pnl не выполнен."
            onRetry={load}
          />
        </div>
      ) : loading && !data ? (
        <SkeletonCards count={6} />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <KPICard
            title="Total Trades"
            value={data ? formatCount(data.total_trades) : '—'}
            icon={Activity}
            tooltip={GLOSSARY['Total Trades']}
            hint={data ? `в среднем ${formatDuration(data.avg_trade_duration_ms)}` : undefined}
          />
          <KPICard
            title="Win Rate"
            value={data ? formatPct(data.win_rate, 1) : '—'}
            icon={Percent}
            tooltip={GLOSSARY['Win Rate']}
            hint={data ? `${formatCount(data.winning_trades)} прибыльных` : undefined}
          />
          <KPICard
            title="Net P&L"
            value={data ? formatUsd(data.total_net_pnl, true) : '—'}
            icon={Wallet}
            accent={data ? (data.total_net_pnl >= 0 ? 'pos' : 'neg') : 'default'}
            tooltip={GLOSSARY['Net P&L (analytics)']}
          />
          <KPICard
            title="Gross P&L"
            value={data ? formatUsd(data.total_gross_pnl, true) : '—'}
            icon={TrendingUp}
            accent={data ? (data.total_gross_pnl >= 0 ? 'pos' : 'neg') : 'default'}
            tooltip={GLOSSARY['Gross P&L (analytics)']}
          />
          <KPICard
            title="Best Trade"
            value={data ? formatUsd(data.best_trade, true) : '—'}
            icon={Award}
            accent={data && data.best_trade >= 0 ? 'pos' : 'default'}
            tooltip={GLOSSARY['Best Trade']}
          />
          <KPICard
            title="Worst Trade"
            value={data ? formatUsd(data.worst_trade, true) : '—'}
            icon={TrendingDown}
            accent={data && data.worst_trade < 0 ? 'neg' : 'default'}
            tooltip={GLOSSARY['Worst Trade']}
          />
        </div>
      )}

      <Panel title="Cumulative net P&L">
        {loading && !data ? <Skeleton className="h-[240px] w-full" /> : <CumulativePnLChart data={daily} />}
      </Panel>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel title="Net P&L по дням">
          {loading && !data ? <Skeleton className="h-[240px] w-full" /> : <DailyPnLChart data={daily} />}
        </Panel>
        <Panel title="Сделок по дням">
          {loading && !data ? <Skeleton className="h-[240px] w-full" /> : <TradesPerDayChart data={daily} />}
        </Panel>
      </div>
    </div>
  )
}
