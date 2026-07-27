import { create } from 'zustand'
import type { Opportunity, Trade } from '../types'

type WsStatus = 'connecting' | 'connected' | 'disconnected'

/** Последний известный bid/ask пары на бирже (WS-канал `prices`). */
export interface LivePrice {
  bid: number
  ask: number
  ts: number // epoch ms тика на бирже (received_at коллектора)
}

/** Ключ карты живых цен. */
export const priceKey = (exchange: string, symbol: string) => `${exchange}:${symbol}`

interface DashboardState {
  wsStatus: WsStatus
  opportunities: Opportunity[]
  trades: Trade[]
  lastSeen: Record<string, number> // exchange -> epoch ms последнего тика (из WS)
  prices: Record<string, LivePrice> // priceKey(exchange, symbol) -> последний bid/ask
  setWsStatus: (s: WsStatus) => void
  setOpportunities: (o: Opportunity[]) => void
  addOpportunity: (o: Opportunity) => void
  setTrades: (t: Trade[]) => void
  addTrade: (t: Trade) => void
  markSeen: (exchanges: string[]) => void
  updatePrices: (items: { exchange: string; symbol: string; bid: number; ask: number; ts?: number }[]) => void
}

export const useDashboardStore = create<DashboardState>((set) => ({
  wsStatus: 'connecting',
  opportunities: [],
  trades: [],
  lastSeen: {},
  prices: {},
  setWsStatus: (s) => set({ wsStatus: s }),
  setOpportunities: (o) => set({ opportunities: o }),
  addOpportunity: (o) =>
    set((st) =>
      st.opportunities.some((x) => x.id === o.id)
        ? st
        : { opportunities: [o, ...st.opportunities].slice(0, 50) },
    ),
  setTrades: (t) => set({ trades: t }),
  addTrade: (t) =>
    set((st) =>
      st.trades.some((x) => x.id === t.id) ? st : { trades: [t, ...st.trades].slice(0, 50) },
    ),
  markSeen: (exchanges) =>
    set((st) => {
      const now = Date.now()
      const next = { ...st.lastSeen }
      for (const e of exchanges) next[e] = now
      return { lastSeen: next }
    }),
  updatePrices: (items) =>
    set((st) => {
      const now = Date.now()
      let changed = false
      const next = { ...st.prices }
      for (const p of items) {
        if (!p.exchange || !p.symbol) continue
        const key = priceKey(p.exchange, p.symbol)
        const prev = next[key]
        const ts = p.ts ?? now
        // Срез приходит раз в секунду целиком: без сравнения с предыдущим
        // значением каждая ячейка таблицы ререндерилась бы ежесекундно,
        // даже когда цена не менялась.
        if (prev && prev.bid === p.bid && prev.ask === p.ask && Math.abs(prev.ts - ts) < 1000) {
          continue
        }
        next[key] = { bid: p.bid, ask: p.ask, ts }
        changed = true
      }
      return changed ? { prices: next } : st
    }),
}))
