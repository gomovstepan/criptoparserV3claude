import { Suspense, lazy, useCallback, useEffect, useState } from 'react'
import { Wallet, TrendingUp, ArrowLeftRight, Gauge, Wifi, WifiOff, ServerCrash } from 'lucide-react'
import api from '../lib/api'
import { useDashboardStore } from '../store/dashboardStore'
import type { Stats, ExchangeStatus, PnLPoint } from '../types'
import { GLOSSARY } from '../lib/glossary'
import { formatCount, formatPct, formatUsd } from '../lib/format'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import KPICard from '../components/KPICard'
import ExchangeStatusCard from '../components/ExchangeStatusCard'
import OpportunitiesTable from '../components/OpportunitiesTable'
import RecentTradesTable from '../components/RecentTradesTable'
import Panel from '../components/Panel'
import Tooltip from '../components/Tooltip'
import EmptyState from '../components/EmptyState'
import { Skeleton, SkeletonCards } from '../components/LoadingSkeleton'
import { asArray, cn } from '../lib/utils'

// Recharts (~350 КБ) грузится отдельным чанком уже после первой отрисовки
const PnLChart = lazy(() => import('../components/PnLChart'))

const POLL_MS = 15000
const WS_FRESH_MS = 15000

export default function Dashboard() {
  useDocumentTitle('Dashboard')

  const wsStatus = useDashboardStore((s) => s.wsStatus)
  const opportunities = useDashboardStore((s) => s.opportunities)
  const trades = useDashboardStore((s) => s.trades)
  const lastSeen = useDashboardStore((s) => s.lastSeen)

  const [stats, setStats] = useState<Stats | null>(null)
  const [exStatus, setExStatus] = useState<ExchangeStatus[]>([])
  const [pnl, setPnl] = useState<PnLPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)

  /** Первичная загрузка: если она не удалась, показываем ошибку с кнопкой повтора. */
  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [s, ex, p, opp, tr] = await Promise.all([
        api.get('/api/v1/stats'),
        api.get('/api/v1/exchanges/status'),
        api.get('/api/v1/stats/pnl?hours=24'),
        api.get('/api/v1/opportunities?limit=8'),
        api.get('/api/v1/trades?page=1&page_size=8'),
      ])
      setStats(s.data)
      setExStatus(asArray<ExchangeStatus>(ex.data?.items))
      setPnl(asArray<PnLPoint>(p.data?.points))
      useDashboardStore.getState().setOpportunities(asArray(opp.data?.items))
      useDashboardStore.getState().setTrades(asArray(tr.data?.items))
      setFailed(false)
    } catch {
      setFailed(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAll()

    const tick = () => {
      // В неактивной вкладке не опрашиваем: три лишних запроса каждые 15 секунд
      if (document.hidden) return
      api.get('/api/v1/stats').then((r) => setStats(r.data)).catch(() => undefined)
      api
        .get('/api/v1/exchanges/status')
        .then((r) => setExStatus(asArray<ExchangeStatus>(r.data?.items)))
        .catch(() => undefined)
      api
        .get('/api/v1/stats/pnl?hours=24')
        .then((r) => setPnl(asArray<PnLPoint>(r.data?.points)))
        .catch(() => undefined)
    }
    const id = window.setInterval(tick, POLL_MS)
    return () => window.clearInterval(id)
  }, [loadAll])

  // Биржа online, если по WS был тик за 15с, иначе — по REST-статусу
  const isOnline = (ex: ExchangeStatus) => {
    const seen = lastSeen[ex.exchange]
    if (seen && Date.now() - seen < WS_FRESH_MS) return true
    return ex.status === 'connected'
  }

  const wsConnected = wsStatus === 'connected'

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-ink">Dashboard</h1>
        <div
          className={cn(
            'flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs',
            wsConnected ? 'border-success/40 text-success' : 'border-warning/40 text-warning',
          )}
        >
          {wsConnected ? <Wifi size={14} aria-hidden="true" /> : <WifiOff size={14} aria-hidden="true" />}
          <Tooltip text={GLOSSARY['WS Status']}>WS: {wsStatus}</Tooltip>
        </div>
      </div>

      {failed && !stats ? (
        <div className="rounded-xl border border-edge bg-surface p-4">
          <EmptyState
            tone="danger"
            icon={ServerCrash}
            title="Не удалось загрузить данные"
            hint="api-gateway не ответил. Проверьте, что стек запущен, и повторите запрос."
            onRetry={loadAll}
          />
        </div>
      ) : loading && !stats ? (
        <SkeletonCards count={4} />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KPICard
            title="Total P&L"
            value={stats ? formatUsd(stats.total_pnl, true) : '—'}
            icon={Wallet}
            accent={stats ? (stats.total_pnl >= 0 ? 'pos' : 'neg') : 'default'}
            tooltip={GLOSSARY['Total P&L']}
          />
          <KPICard
            title="Active Opportunities"
            value={stats ? formatCount(stats.active_opportunities) : '—'}
            icon={TrendingUp}
            tooltip={GLOSSARY['Active Opportunities']}
          />
          <KPICard
            title="Today's Trades"
            value={stats ? formatCount(stats.trades_today) : '—'}
            icon={ArrowLeftRight}
            tooltip={GLOSSARY["Today's Trades"]}
          />
          <KPICard
            title="Best Spread"
            value={stats ? formatPct(stats.best_spread_pct, 3) : '—'}
            icon={Gauge}
            accent={stats && stats.best_spread_pct >= 0 ? 'pos' : 'default'}
            tooltip={GLOSSARY['Best Spread']}
          />
        </div>
      )}

      <Panel title="Exchange Status" titleTooltip={GLOSSARY['Exchange Status']}>
        {exStatus.length === 0 ? (
          <EmptyState
            compact
            icon={ServerCrash}
            title="Статус бирж недоступен"
            hint="Коллектор ещё не публиковал тики или сервис недоступен."
          />
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
            {exStatus.map((ex) => (
              <ExchangeStatusCard
                key={ex.exchange}
                exchange={ex.exchange}
                online={isOnline(ex)}
                latencyMs={ex.latency_ms}
              />
            ))}
          </div>
        )}
      </Panel>

      <Panel title="P&L (24h)" titleTooltip={GLOSSARY['P&L (24h)']}>
        <Suspense fallback={<Skeleton className="h-[220px] w-full" />}>
          <PnLChart data={pnl} />
        </Suspense>
      </Panel>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel title="Top Opportunities" right={<span className="text-xs text-muted">real-time</span>}>
          <OpportunitiesTable
            items={opportunities.slice(0, 8)}
            loading={loading && opportunities.length === 0}
          />
        </Panel>
        <Panel title="Recent Trades" right={<span className="text-xs text-muted">real-time</span>}>
          <RecentTradesTable items={trades.slice(0, 8)} loading={loading && trades.length === 0} />
        </Panel>
      </div>
    </div>
  )
}
