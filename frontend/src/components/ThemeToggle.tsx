import { Moon, Sun } from 'lucide-react'
import { useThemeStore } from '../store/themeStore'

/** Переключатель темы оформления (тёмная/светлая). */
export default function ThemeToggle() {
  const theme = useThemeStore((s) => s.theme)
  const toggle = useThemeStore((s) => s.toggle)
  const isDark = theme === 'dark'
  return (
    <button
      onClick={toggle}
      aria-label={isDark ? 'Светлая тема' : 'Тёмная тема'}
      title={isDark ? 'Светлая тема' : 'Тёмная тема'}
      className="flex h-8 w-8 items-center justify-center rounded-lg text-muted transition-colors hover:bg-surface2 hover:text-ink"
    >
      {isDark ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  )
}
