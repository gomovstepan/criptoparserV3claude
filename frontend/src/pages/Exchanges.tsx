import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import api from '../lib/api'
import type { ExchangeConfig, ExchangeConnStatus } from '../types'
import Panel from '../components/Panel'
import Toggle from '../components/Toggle'
import { cn } from '../lib/utils'

interface StatusRow {
  exchange: string
  status: ExchangeConnStatus
  latency_ms: number | null
  last_tick: string | null
}

const STATUS_STYLES: Record<ExchangeConnStatus, string> = {
  connected: 'bg-success/15 text-success',
  stale: 'bg-warning/15 text-warning',
  disconnected: 'bg-danger/15 text-danger',
}

const STATUS_LABELS: Record<ExchangeConnStatus, string> = {
  connected: 'Онлайн',
  stale: 'Устарел',
  disconnected: 'Офлайн',
}

function StatusBadge({ status }: { status: ExchangeConnStatus }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium', STATUS_STYLES[status])}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {STATUS_LABELS[status]}
    </span>
  )
}

export default function Exchanges() {
  const [configs, setConfigs] = useState<ExchangeConfig[]>([])
  const [status, setStatus] = useState<Record<string, StatusRow>>({})
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState<string | null>(null)

  const load = async () => {
    try {
      const [cfgRes, stRes] = await Promise.all([
        api.get('/api/v1/exchanges'),
        api.get('/api/v1/exchanges/status'),
      ])
      setConfigs(cfgRes.data.items)
      const map: Record<string, StatusRow> = {}
      for (const s of stRes.data.items) map[s.exchange] = s
      setStatus(map)
    } catch {
      toast.error('Не удалось загрузить биржи')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 15000)
    return () => clearInterval(id)
  }, [])

  const toggleActive = async (cfg: ExchangeConfig) => {
    const next = !cfg.is_active
    setPending(cfg.exchange)
    // Оптимистично обновляем UI
    setConfigs((prev) => prev.map((c) => (c.exchange === cfg.exchange ? { ...c, is_active: next } : c)))
    try {
      await api.patch(`/api/v1/exchanges/${cfg.exchange}`, { is_active: next })
      toast.success(`${cfg.exchange}: ${next ? 'включена' : 'выключена'}`)
    } catch {
      // Откат при ошибке
      setConfigs((prev) => prev.map((c) => (c.exchange === cfg.exchange ? { ...c, is_active: cfg.is_active } : c)))
      toast.error(`Не удалось изменить ${cfg.exchange}`)
    } finally {
      setPending(null)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-ink">Exchanges</h1>

      <Panel title={`Биржи (${configs.length})`}>
        {loading ? (
          <div className="py-10 text-center text-sm text-muted">Загрузка…</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-edge text-left text-xs uppercase tracking-wide text-muted">
                  <th className="px-3 py-2 font-medium">Биржа</th>
                  <th className="px-3 py-2 font-medium">Статус</th>
                  <th className="px-3 py-2 text-right font-medium">Maker fee</th>
                  <th className="px-3 py-2 text-right font-medium">Taker fee</th>
                  <th className="px-3 py-2 text-right font-medium">Вывод USDT</th>
                  <th className="px-3 py-2 text-right font-medium">Rate limit</th>
                  <th className="px-3 py-2 text-center font-medium">Активна</th>
                </tr>
              </thead>
              <tbody>
                {configs.map((cfg) => {
                  const st = status[cfg.exchange]
                  return (
                    <tr key={cfg.exchange} className="border-b border-edge/50 last:border-0">
                      <td className="px-3 py-2.5 font-medium capitalize text-ink">{cfg.exchange}</td>
                      <td className="px-3 py-2.5">
                        <StatusBadge status={st?.status ?? 'disconnected'} />
                      </td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-muted">{cfg.maker_fee_pct.toFixed(3)}%</td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-muted">{cfg.taker_fee_pct.toFixed(3)}%</td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-muted">
                        {cfg.withdrawal_usdt != null ? `$${cfg.withdrawal_usdt.toFixed(2)}` : '—'}
                      </td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-muted">
                        {cfg.rate_limit_req_per_sec != null ? `${cfg.rate_limit_req_per_sec}/s` : '—'}
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex justify-center">
                          <Toggle
                            checked={cfg.is_active}
                            disabled={pending === cfg.exchange}
                            onChange={() => toggleActive(cfg)}
                            label={`Биржа ${cfg.exchange}`}
                          />
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <p className="text-xs text-muted">
        Переключатель сохраняет флаг <code className="text-ink">is_active</code> сразу. Фактическое
        подключение/отключение биржи в коллекторе применится после его рестарта.
      </p>
    </div>
  )
}
