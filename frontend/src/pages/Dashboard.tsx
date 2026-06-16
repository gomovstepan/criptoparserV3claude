import { useEffect, useState } from 'react'
import { Wallet, TrendingUp, ArrowLeftRight, Gauge, Wifi, WifiOff } from 'lucide-react'
import api from '../lib/api'
import { useDashboardStore } from '../store/dashboardStore'
import type { Stats, ExchangeStatus, PnLPoint } from '../types'
import KPICard from '../components/KPICard'
import ExchangeStatusCard from '../components/ExchangeStatusCard'
import PnLChart from '../components/PnLChart'
import OpportunitiesTable from '../components/OpportunitiesTable'
import RecentTradesTable from '../components/RecentTradesTable'
import Panel from '../components/Panel'
import { SkeletonCards, SkeletonTable } from '../components/LoadingSkeleton'
import { cn } from '../lib/utils'

export default function Dashboard() {
  const wsStatus = useDashboardStore((s) => s.wsStatus)
  const opportunities = useDashboardStore((s) => s.opportunities)
  const trades = useDashboardStore((s) => s.trades)
  const lastSeen = useDashboardStore((s) => s.lastSeen)
  const [stats, setStats] = useState<Stats | null>(null)
  const [exStatus, setExStatus] = useState<ExchangeStatus[]>([])
  const [pnl, setPnl] = useState<PnLPoint[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadAll = async () => {
      const [s, ex, p, opp, tr] = await Promise.all([
        api.get('/api/v1/stats'),
        api.get('/api/v1/exchanges/status'),
        api.get('/api/v1/stats/pnl?hours=24'),
        api.get('/api/v1/opportunities?limit=8'),
        api.get('/api/v1/trades?page=1&page_size=8'),
      ])
      setStats(s.data)
      setExStatus(ex.data.items)
      setPnl(p.data.points)
      useDashboardStore.getState().setOpportunities(opp.data.items)
      useDashboardStore.getState().setTrades(tr.data.items)
    }
    loadAll()
      .catch(() => undefined)
      .finally(() => setLoading(false))

    const id = window.setInterval(() => {
      api.get('/api/v1/stats').then((r) => setStats(r.data)).catch(() => undefined)
      api.get('/api/v1/exchanges/status').then((r) => setExStatus(r.data.items)).catch(() => undefined)
      api.get('/api/v1/stats/pnl?hours=24').then((r) => setPnl(r.data.points)).catch(() => undefined)
    }, 15000)
    return () => window.clearInterval(id)
  }, [])

  // Биржа online, если по WS был тик за 15с, иначе — по REST-статусу
  const isOnline = (ex: ExchangeStatus) => {
    const seen = lastSeen[ex.exchange]
    if (seen && Date.now() - seen < 15000) return true
    return ex.status === 'connected'
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-ink">Dashboard</h1>
        <div
          className={cn(
            'flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs',
            wsStatus === 'connected'
              ? 'border-success/30 text-success'
              : 'border-warning/30 text-warning',
          )}
        >
          {wsStatus === 'connected' ? <Wifi size={14} /> : <WifiOff size={14} />}
          WS: {wsStatus}
        </div>
      </div>

      {loading && !stats ? (
        <SkeletonCards count={4} />
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <KPICard
            title="Total P&L"
            value={stats ? `$${stats.total_pnl.toFixed(2)}` : '…'}
            icon={Wallet}
            accent={stats ? (stats.total_pnl >= 0 ? 'pos' : 'neg') : 'default'}
          />
          <KPICard
            title="Active Opportunities"
            value={stats ? String(stats.active_opportunities) : '…'}
            icon={TrendingUp}
          />
          <KPICard
            title="Today's Trades"
            value={stats ? String(stats.trades_today) : '…'}
            icon={ArrowLeftRight}
          />
          <KPICard
            title="Best Spread"
            value={stats ? `${stats.best_spread_pct.toFixed(3)}%` : '…'}
            icon={Gauge}
            accent="pos"
          />
        </div>
      )}

      <Panel title="Exchange Status">
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
      </Panel>

      <Panel title="P&L (24h)">
        <PnLChart data={pnl} />
      </Panel>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel title="Top Opportunities" right={<span className="text-xs text-muted">real-time</span>}>
          {loading && opportunities.length === 0 ? (
            <SkeletonTable rows={6} cols={5} />
          ) : (
            <OpportunitiesTable items={opportunities.slice(0, 8)} />
          )}
        </Panel>
        <Panel title="Recent Trades" right={<span className="text-xs text-muted">real-time</span>}>
          {loading && trades.length === 0 ? (
            <SkeletonTable rows={6} cols={5} />
          ) : (
            <RecentTradesTable items={trades.slice(0, 8)} />
          )}
        </Panel>
      </div>
    </div>
  )
}
