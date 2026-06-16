import { useEffect, useState } from 'react'
import { WifiOff } from 'lucide-react'
import { useDashboardStore } from '../store/dashboardStore'

/** Глобальный индикатор проблем со связью: баннер, когда браузер офлайн
 *  или WebSocket надолго отвалился. Висит поверх контента сверху. */
export default function NetworkStatus() {
  const [online, setOnline] = useState(navigator.onLine)
  const wsStatus = useDashboardStore((s) => s.wsStatus)

  useEffect(() => {
    const up = () => setOnline(true)
    const down = () => setOnline(false)
    window.addEventListener('online', up)
    window.addEventListener('offline', down)
    return () => {
      window.removeEventListener('online', up)
      window.removeEventListener('offline', down)
    }
  }, [])

  const offline = !online
  const wsDown = wsStatus === 'disconnected'
  if (!offline && !wsDown) return null

  const text = offline
    ? 'Нет подключения к интернету'
    : 'Соединение с сервером потеряно — переподключаемся…'

  return (
    <div className="flex items-center justify-center gap-2 bg-danger/90 px-4 py-1.5 text-center text-xs font-medium text-white">
      <WifiOff size={14} />
      {text}
    </div>
  )
}
