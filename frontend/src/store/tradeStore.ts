import { create } from 'zustand'
import api from '../lib/api'
import { asArray, asNumber } from '../lib/utils'
import type { Trade } from '../types'

export interface TradeFilters {
  status: string
  symbol: string
  exchange: string
  start: string // YYYY-MM-DD или ''
  end: string
}

const emptyFilters: TradeFilters = { status: '', symbol: '', exchange: '', start: '', end: '' }

// Порядковый номер запроса fetch(): ответ с несовпадающим номером устарел.
let fetchSeq = 0

interface TradeState {
  items: Trade[]
  total: number
  page: number
  pageSize: number
  totalPages: number
  loading: boolean
  filters: TradeFilters
  selected: Trade | null
  setFilter: (key: keyof TradeFilters, value: string) => void
  resetFilters: () => void
  setPage: (p: number) => void
  setPageSize: (n: number) => void
  select: (t: Trade | null) => void
  fetch: () => Promise<void>
  deleteFiltered: () => Promise<{ deleted: number; truncated: boolean }>
}

export function hasActiveFilters(f: TradeFilters): boolean {
  return Boolean(f.status || f.symbol || f.exchange || f.start || f.end)
}

/** Построить query-params из фильтров (используется и стором, и кнопкой Export). */
export function filtersToParams(filters: TradeFilters): Record<string, string> {
  const p: Record<string, string> = {}
  if (filters.status) p.status = filters.status
  if (filters.symbol) p.symbol = filters.symbol
  if (filters.exchange) p.exchange = filters.exchange
  if (filters.start) p.start = filters.start
  if (filters.end) p.end = `${filters.end}T23:59:59`
  return p
}

export const useTradeStore = create<TradeState>((set, get) => ({
  items: [],
  total: 0,
  page: 1,
  pageSize: 25,
  totalPages: 0,
  loading: false,
  filters: { ...emptyFilters },
  selected: null,
  setFilter: (key, value) => set((s) => ({ filters: { ...s.filters, [key]: value }, page: 1 })),
  resetFilters: () => set({ filters: { ...emptyFilters }, page: 1 }),
  setPage: (p) => set({ page: p }),
  setPageSize: (n) => set({ pageSize: n, page: 1 }),
  select: (t) => set({ selected: t }),
  fetch: async () => {
    // Быстрое переключение фильтров/страниц порождает параллельные запросы;
    // без порядкового номера медленный устаревший ответ затирал бы свежий.
    const seq = ++fetchSeq
    const { page, pageSize, filters } = get()
    set({ loading: true })
    try {
      const params = { page: String(page), page_size: String(pageSize), ...filtersToParams(filters) }
      const r = await api.get('/api/v1/trades', { params })
      if (seq !== fetchSeq) return
      set({
        items: asArray<Trade>(r.data?.items),
        total: asNumber(r.data?.total),
        totalPages: asNumber(r.data?.total_pages),
        loading: false,
      })
    } catch {
      if (seq === fetchSeq) set({ loading: false })
    }
  },
  deleteFiltered: async () => {
    const { filters } = get()
    const r = await api.delete('/api/v1/trades', { params: filtersToParams(filters) })
    set({ page: 1 })
    await get().fetch()
    return r.data as { deleted: number; truncated: boolean }
  },
}))
