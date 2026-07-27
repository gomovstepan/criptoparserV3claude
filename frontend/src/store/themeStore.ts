import { create } from 'zustand'

export type Theme = 'dark' | 'light'

function apply(theme: Theme) {
  const el = document.documentElement
  // Держим оба класса в актуальном состоянии: `light` включает светлые токены,
  // `dark` нужен варианту darkMode:'class' в tailwind. Раньше снимался только
  // `light`, и в светлой теме на <html> оставался класс `dark`.
  el.classList.toggle('light', theme === 'light')
  el.classList.toggle('dark', theme === 'dark')
  el.style.colorScheme = theme
}

function readInitial(): Theme {
  const stored = localStorage.getItem('theme')
  if (stored === 'light' || stored === 'dark') return stored
  // Первый визит — уважаем системную настройку (prefers-color-scheme)
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

const initial: Theme = readInitial()
// Применяем сразу при загрузке модуля — до первого рендера, чтобы не мигало.
apply(initial)

interface ThemeState {
  theme: Theme
  toggle: () => void
  setTheme: (t: Theme) => void
}

/** Тема оформления (dark/light). Персистится в localStorage, класс на <html>. */
export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: initial,
  toggle: () => get().setTheme(get().theme === 'dark' ? 'light' : 'dark'),
  setTheme: (theme) => {
    localStorage.setItem('theme', theme)
    apply(theme)
    set({ theme })
  },
}))
