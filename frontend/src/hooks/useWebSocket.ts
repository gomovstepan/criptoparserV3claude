import { useEffect, useRef } from 'react'
import { useAuthStore } from '../store/authStore'
import { useDashboardStore } from '../store/dashboardStore'
import { normalizeOpportunity, normalizeTrade } from '../lib/normalize'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws'
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
            store.markSeen(msg.data.map((p: { exchange: string }) => p.exchange))
          }
        } catch {
          /* игнорируем некорректные сообщения */
        }
      }

      ws.onclose = () => {
        clearTimers()
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
      wsRef.current?.close()
    }
  }, [])
}
