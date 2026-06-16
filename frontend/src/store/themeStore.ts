import { create } from 'zustand'

export type Theme = 'dark' | 'light'

function apply(theme: Theme) {
  const el = document.documentElement
  el.classList.toggle('light', theme === 'light')
}

const initial: Theme = (localStorage.getItem('theme') as Theme) || 'dark'
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
