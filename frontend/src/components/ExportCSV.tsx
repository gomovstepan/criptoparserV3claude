import { useState } from 'react'
import { Download } from 'lucide-react'
import api from '../lib/api'
import { filtersToParams, type TradeFilters } from '../store/tradeStore'

/** Кнопка выгрузки текущей выборки сделок в CSV (через blob-скачивание). */
export default function ExportCSV({ filters }: { filters: TradeFilters }) {
  const [busy, setBusy] = useState(false)

  const onExport = async () => {
    setBusy(true)
    try {
      const r = await api.get('/api/v1/trades/export', {
        params: filtersToParams(filters),
        responseType: 'blob',
      })
      const url = URL.createObjectURL(r.data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'trades.csv'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } finally {
      setBusy(false)
    }
  }

  return (
    <button
      onClick={onExport}
      disabled={busy}
      className="flex items-center gap-2 self-end rounded-lg border border-edge bg-surface2 px-3 py-2 text-sm text-ink hover:border-accent disabled:opacity-50"
    >
      <Download size={16} />
      {busy ? 'Экспорт…' : 'Export CSV'}
    </button>
  )
}
