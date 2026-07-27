import { Moon, Sun } from 'lucide-react'
import { useThemeStore } from '../store/themeStore'
import Button from './Button'

/** Переключатель темы оформления (тёмная/светлая). */
export default function ThemeToggle() {
  const theme = useThemeStore((s) => s.theme)
  const toggle = useThemeStore((s) => s.toggle)
  const isDark = theme === 'dark'
  const label = isDark ? 'Включить светлую тему' : 'Включить тёмную тему'
  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label={label} title={label} aria-pressed={!isDark}>
      {isDark ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
    </Button>
  )
}
