import { useState } from 'react'
import { Download } from 'lucide-react'
import { toast } from 'sonner'
import api from '../lib/api'
import { filtersToParams, type TradeFilters } from '../store/tradeStore'
import Button from './Button'

/** Кнопка выгрузки текущей выборки сделок в CSV (через blob-скачивание). */
export default function ExportCSV({ filters }: { filters: TradeFilters }) {
  const [busy, setBusy] = useState(false)

  const onExport = async () => {
    setBusy(true)
    let url: string | null = null
    try {
      const r = await api.get('/api/v1/trades/export', {
        params: filtersToParams(filters),
        responseType: 'blob',
      })
      url = URL.createObjectURL(r.data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `trades-${new Date().toISOString().slice(0, 10)}.csv`
      document.body.appendChild(a)
      a.click()
      a.remove()
      toast.success('Файл выгружен')
    } catch {
      // Раньше ошибка проглатывалась: пользователь жал кнопку и не получал ничего
      toast.error('Не удалось выгрузить CSV. Попробуйте ещё раз.')
    } finally {
      // Отзываем ссылку не сразу: часть браузеров обрывает уже начатую загрузку
      if (url) {
        const objectUrl = url
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 30_000)
      }
      setBusy(false)
    }
  }

  return (
    <Button onClick={onExport} loading={busy} loadingText="Экспорт…">
      <Download size={16} aria-hidden="true" />
      Export CSV
    </Button>
  )
}
