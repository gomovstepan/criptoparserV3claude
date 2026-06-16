import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, Menu } from 'lucide-react'
import api from '../lib/api'
import { useAuthStore } from '../store/authStore'
import { cn } from '../lib/utils'
import ThemeToggle from './ThemeToggle'

/** Верхняя панель: гамбургер (mobile) + статус системы (опрос /health) + пользователь + выход. */
export default function Navbar({ onMenuClick }: { onMenuClick: () => void }) {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const [online, setOnline] = useState<boolean | null>(null)

  useEffect(() => {
    let active = true
    const check = async () => {
      try {
        const { data } = await api.get('/health')
        if (active) setOnline(data.status === 'healthy')
      } catch {
        if (active) setOnline(false)
      }
    }
    check()
    const id = setInterval(check, 10000)
    return () => {
      active = false
      clearInterval(id)
    }
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="flex h-14 items-center justify-between border-b border-edge bg-surface px-6">
      <div className="flex items-center gap-2 text-sm">
        <button
          onClick={onMenuClick}
          aria-label="Открыть меню"
          className="text-muted transition-colors hover:text-ink md:hidden"
        >
          <Menu size={20} />
        </button>
        <span
          className={cn(
            'h-2.5 w-2.5 rounded-full',
            online === null ? 'bg-warning' : online ? 'bg-success' : 'bg-danger',
          )}
        />
        <span className="text-muted">
          {online === null ? 'Проверка…' : online ? 'Система онлайн' : 'Система офлайн'}
        </span>
      </div>
      <div className="flex items-center gap-4">
        <ThemeToggle />
        <span className="text-sm text-muted">{user}</span>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm text-muted transition-colors hover:bg-surface2 hover:text-ink"
        >
          <LogOut size={16} />
          Выйти
        </button>
      </div>
    </header>
  )
}
