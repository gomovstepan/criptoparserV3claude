import { useEffect, useRef } from 'react'
import { useAuthStore } from '../store/authStore'
import { useDashboardStore } from '../store/dashboardStore'
import { normalizeOpportunity, normalizeTrade } from '../lib/normalize'

const WS_URL = import.meta.env.VITE_WS_URL || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
const MAX_BACKOFF_MS = 30000
const PING_INTERVAL_MS = 20000 // как часто шлём ping
const LIVENESS_TIMEOUT_MS = 45000 // нет активности дольше — соединение мёртвое

/**
 * Подключение к WebSocket api-gateway с авто-reconnect (exponential backoff)
 * и heartbeat (ping/pong + watchdog по liveness).
 * Обновляет dashboardStore по каналам: opportunities, trades, prices.
 */
export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const attemptRef = useRef(0)
  const closedRef = useRef(false)
  const timerRef = useRef<number | undefined>(undefined)
  const pingRef = useRef<number | undefined>(undefined)
  const watchdogRef = useRef<number | undefined>(undefined)
  const lastActivityRef = useRef(Date.now())

  useEffect(() => {
    closedRef.current = false

    const clearTimers = () => {
      if (pingRef.current) window.clearInterval(pingRef.current)
      if (watchdogRef.current) window.clearInterval(watchdogRef.current)
    }

    const connect = () => {
      const token = useAuthStore.getState().token
      useDashboardStore.getState().setWsStatus('connecting')
      const ws = new WebSocket(`${WS_URL}?token=${token ?? ''}`)
      wsRef.current = ws

      ws.onopen = () => {
        attemptRef.current = 0
        lastActivityRef.current = Date.now()
        useDashboardStore.getState().setWsStatus('connected')
        // Heartbeat: периодический ping + watchdog по последней активности.
        pingRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }))
        }, PING_INTERVAL_MS)
        watchdogRef.current = window.setInterval(() => {
          if (Date.now() - lastActivityRef.current > LIVENESS_TIMEOUT_MS) ws.close()
        }, PING_INTERVAL_MS)
      }

      ws.onmessage = (ev) => {
        lastActivityRef.current = Date.now() // любая активность = живо (вкл. pong)
        try {
          const msg = JSON.parse(ev.data)
          const store = useDashboardStore.getState()
          if (msg.channel === 'opportunities') {
            store.addOpportunity(normalizeOpportunity(msg.data))
          } else if (msg.channel === 'trades') {
            store.addTrade(normalizeTrade(msg.data))
          } else if (msg.channel === 'prices' && Array.isArray(msg.data)) {
            const items = msg.data as {
              exchange: string
              symbol: string
              bid: number
              ask: number
              ts?: number
            }[]
            // Возраст тика считаем в СЕРВЕРНЫХ часах (msg.now - ts) и
            // пересаживаем на часы клиента: прямое сравнение ts с Date.now()
            // ломалось бы от дрейфа часов браузера/контейнера (>15с — и все
            // цены навсегда «устаревшие»). Срез накопительный, поэтому живость
            // биржи определяется только свежими тиками.
            const serverNow = typeof msg.now === 'number' ? msg.now : undefined
            const clientNow = Date.now()
            const age = (ts?: number) =>
              ts !== undefined && serverNow !== undefined ? Math.max(0, serverNow - ts) : 0
            store.markSeen(items.filter((p) => age(p.ts) < 15_000).map((p) => p.exchange))
            store.updatePrices(items.map((p) => ({ ...p, ts: clientNow - age(p.ts) })))
          }
        } catch {
          /* игнорируем некорректные сообщения */
        }
      }

      ws.onclose = () => {
        clearTimers()
        // Призрак от прошлого mount'а (StrictMode размонтирует и монтирует
        // повторно): его onclose не должен ни трогать статус, ни планировать
        // reconnect — иначе живут два параллельных сокета.
        if (ws !== wsRef.current) return
        useDashboardStore.getState().setWsStatus('disconnected')
        if (closedRef.current) return
        const delay = Math.min(MAX_BACKOFF_MS, 1000 * 2 ** attemptRef.current)
        attemptRef.current += 1
        timerRef.current = window.setTimeout(connect, delay)
      }

      ws.onerror = () => ws.close()
    }

    connect()

    return () => {
      closedRef.current = true
      clearTimers()
      if (timerRef.current) window.clearTimeout(timerRef.current)
      const ws = wsRef.current
      wsRef.current = null // onclose закрываемого сокета увидит несовпадение и замолчит
      ws?.close()
    }
  }, [])
}
