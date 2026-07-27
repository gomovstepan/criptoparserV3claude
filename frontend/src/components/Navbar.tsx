import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, Menu } from 'lucide-react'
import api from '../lib/api'
import { useAuthStore } from '../store/authStore'
import { cn } from '../lib/utils'
import ThemeToggle from './ThemeToggle'
import Button from './Button'

/** Верхняя панель: гамбургер (mobile) + статус системы (опрос /health) + пользователь + выход. */
export default function Navbar({ onMenuClick }: { onMenuClick: () => void }) {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const [online, setOnline] = useState<boolean | null>(null)

  useEffect(() => {
    let active = true
    const check = async () => {
      // Во вкладке в фоне не опрашиваем — лишние запросы и работа основного потока
      if (document.hidden) return
      try {
        const { data } = await api.get('/health')
        if (active) setOnline(data.status === 'healthy')
      } catch {
        if (active) setOnline(false)
      }
    }
    check()
    const id = window.setInterval(check, 10000)
    document.addEventListener('visibilitychange', check)
    return () => {
      active = false
      window.clearInterval(id)
      document.removeEventListener('visibilitychange', check)
    }
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const label = online === null ? 'Проверка…' : online ? 'Система онлайн' : 'Система офлайн'

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-edge bg-surface px-3 sm:px-6">
      <div className="flex min-w-0 items-center gap-2 text-sm">
        <Button variant="ghost" size="icon" onClick={onMenuClick} aria-label="Открыть меню" className="md:hidden">
          <Menu size={20} aria-hidden="true" />
        </Button>
        {/* role=status: смена состояния озвучивается, но не перехватывает фокус */}
        <span role="status" className="flex items-center gap-2 truncate">
          <span
            aria-hidden="true"
            className={cn(
              'h-2.5 w-2.5 shrink-0 rounded-full',
              online === null ? 'bg-warning' : online ? 'bg-success' : 'bg-danger',
            )}
          />
          <span className="truncate text-muted">{label}</span>
        </span>
      </div>
      <div className="flex shrink-0 items-center gap-2 sm:gap-4">
        <ThemeToggle />
        <span className="hidden max-w-[14rem] truncate text-sm text-muted lg:inline">{user}</span>
        {/* aria-label, а не <span class="sr-only">: sr-only — это position:absolute,
            и без позиционированного предка такой элемент выпадает из потока и
            может растянуть страницу по горизонтали. */}
        <Button variant="ghost" size="sm" onClick={handleLogout} aria-label="Выйти из системы">
          <LogOut size={16} aria-hidden="true" />
          <span className="hidden sm:inline">Выйти</span>
        </Button>
      </div>
    </header>
  )
}
