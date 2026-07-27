import { useCallback, useEffect, useState } from 'react'
import { ServerCrash } from 'lucide-react'
import { toast } from 'sonner'
import api from '../lib/api'
import type { ExchangeConfig, ExchangeConnStatus } from '../types'
import { GLOSSARY } from '../lib/glossary'
import { formatPct, formatUsd } from '../lib/format'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import Panel from '../components/Panel'
import Toggle from '../components/Toggle'
import Tooltip from '../components/Tooltip'
import EmptyState from '../components/EmptyState'
import { SkeletonTable } from '../components/LoadingSkeleton'
import { asArray, cn } from '../lib/utils'

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
    <span
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium',
        STATUS_STYLES[status],
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      {STATUS_LABELS[status]}
    </span>
  )
}

export default function Exchanges() {
  useDocumentTitle('Exchanges')

  const [configs, setConfigs] = useState<ExchangeConfig[]>([])
  const [status, setStatus] = useState<Record<string, StatusRow>>({})
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [pending, setPending] = useState<string | null>(null)

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      const [cfgRes, stRes] = await Promise.all([
        api.get('/api/v1/exchanges'),
        api.get('/api/v1/exchanges/status'),
      ])
      setConfigs(asArray<ExchangeConfig>(cfgRes.data?.items))
      const map: Record<string, StatusRow> = {}
      for (const s of asArray<StatusRow>(stRes.data?.items)) map[s.exchange] = s
      setStatus(map)
      setFailed(false)
    } catch {
      setFailed(true)
      if (!silent) toast.error('Не удалось загрузить биржи')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    // Фоновые обновления — без спиннера и без тостов, чтобы не мигало каждые 15с
    const id = window.setInterval(() => {
      if (!document.hidden) load(true)
    }, 15000)
    return () => window.clearInterval(id)
  }, [load])

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
        {loading && configs.length === 0 ? (
          <SkeletonTable rows={7} cols={5} />
        ) : failed && configs.length === 0 ? (
          <EmptyState
            tone="danger"
            icon={ServerCrash}
            title="Не удалось загрузить список бирж"
            hint="Запрос к /api/v1/exchanges не выполнен."
            onRetry={() => load()}
          />
        ) : (
          <div className="relative overflow-x-auto">
            <table className="w-full text-sm" aria-label="Конфигурация бирж">
              <thead>
                <tr className="border-b border-edge text-left text-xs uppercase tracking-wide text-muted">
                  <th scope="col" className="px-3 py-2 font-medium">
                    <Tooltip text={GLOSSARY['Биржа']}>Биржа</Tooltip>
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    <Tooltip text={GLOSSARY['Статус']}>Статус</Tooltip>
                  </th>
                  <th scope="col" className="px-3 py-2 text-right font-medium">
                    <Tooltip text={GLOSSARY['Maker fee']}>Maker fee</Tooltip>
                  </th>
                  <th scope="col" className="px-3 py-2 text-right font-medium">
                    <Tooltip text={GLOSSARY['Taker fee']}>Taker fee</Tooltip>
                  </th>
                  <th scope="col" className="px-3 py-2 text-right font-medium">
                    <Tooltip text={GLOSSARY['Вывод USDT']}>Вывод USDT</Tooltip>
                  </th>
                  <th scope="col" className="px-3 py-2 text-right font-medium">
                    <Tooltip text={GLOSSARY['Rate limit']}>Rate limit</Tooltip>
                  </th>
                  <th scope="col" className="px-3 py-2 text-center font-medium">
                    <Tooltip text={GLOSSARY['Активна']}>Активна</Tooltip>
                  </th>
                </tr>
              </thead>
              <tbody>
                {configs.map((cfg) => {
                  const st = status[cfg.exchange]
                  return (
                    <tr key={cfg.exchange} className="border-b border-edge/50 last:border-0">
                      <th scope="row" className="px-3 py-3 text-left font-medium capitalize text-ink">
                        {cfg.exchange}
                      </th>
                      <td className="px-3 py-3">
                        <StatusBadge status={st?.status ?? 'disconnected'} />
                      </td>
                      <td className="px-3 py-3 text-right tabular-nums text-muted">
                        {formatPct(cfg.maker_fee_pct, 3)}
                      </td>
                      <td className="px-3 py-3 text-right tabular-nums text-muted">
                        {formatPct(cfg.taker_fee_pct, 3)}
                      </td>
                      <td className="px-3 py-3 text-right tabular-nums text-muted">
                        {cfg.withdrawal_usdt != null ? formatUsd(cfg.withdrawal_usdt) : '—'}
                      </td>
                      <td className="px-3 py-3 text-right tabular-nums text-muted">
                        {cfg.rate_limit_req_per_sec != null ? `${cfg.rate_limit_req_per_sec}/s` : '—'}
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex justify-center">
                          <Toggle
                            checked={cfg.is_active}
                            disabled={pending === cfg.exchange}
                            onChange={() => toggleActive(cfg)}
                            label={`Биржа ${cfg.exchange}: сбор данных`}
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
