import { create } from 'zustand'
import type { Opportunity, Trade } from '../types'

type WsStatus = 'connecting' | 'connected' | 'disconnected'

interface DashboardState {
  wsStatus: WsStatus
  opportunities: Opportunity[]
  trades: Trade[]
  lastSeen: Record<string, number> // exchange -> epoch ms последнего тика (из WS)
  setWsStatus: (s: WsStatus) => void
  setOpportunities: (o: Opportunity[]) => void
  addOpportunity: (o: Opportunity) => void
  setTrades: (t: Trade[]) => void
  addTrade: (t: Trade) => void
  markSeen: (exchanges: string[]) => void
}

export const useDashboardStore = create<DashboardState>((set) => ({
  wsStatus: 'connecting',
  opportunities: [],
  trades: [],
  lastSeen: {},
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
}))
