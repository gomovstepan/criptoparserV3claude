import { fileURLToPath } from 'node:url'
import { dirname } from 'node:path'

// Абсолютные пути с forward-slash — content-globs работают независимо от CWD,
// откуда бы ни запускался Vite (важно для запуска не из папки frontend).
const root = dirname(fileURLToPath(import.meta.url)).replace(/\\/g, '/')

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [`${root}/index.html`, `${root}/src/**/*.{ts,tsx}`],
  theme: {
    extend: {
      colors: {
        // Токены берутся из CSS-переменных (index.css) — переключаются темой.
        page: 'rgb(var(--c-page) / <alpha-value>)',
        surface: 'rgb(var(--c-surface) / <alpha-value>)',
        surface2: 'rgb(var(--c-surface2) / <alpha-value>)',
        edge: 'rgb(var(--c-edge) / <alpha-value>)',
        'edge-strong': 'rgb(var(--c-edge-strong) / <alpha-value>)',
        accent: 'rgb(var(--c-accent) / <alpha-value>)',
        success: 'rgb(var(--c-success) / <alpha-value>)',
        danger: 'rgb(var(--c-danger) / <alpha-value>)',
        warning: 'rgb(var(--c-warning) / <alpha-value>)',
        ink: 'rgb(var(--c-ink) / <alpha-value>)',
        muted: 'rgb(var(--c-muted) / <alpha-value>)',
        // Текст/иконки поверх соответствующей заливки (контраст ≥4.5:1 в обеих темах)
        'on-accent': 'rgb(var(--c-on-accent) / <alpha-value>)',
        'on-success': 'rgb(var(--c-on-success) / <alpha-value>)',
        'on-danger': 'rgb(var(--c-on-danger) / <alpha-value>)',
        'on-warning': 'rgb(var(--c-on-warning) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      // Единая шкала слоёв вместо произвольных значений (было z-[9999] у тултипа)
      zIndex: {
        nav: '30', // шапка / боковое меню на desktop
        drawer: '40', // мобильное меню, боковая панель сделки
        modal: '50', // модальные окна
        tooltip: '60', // подсказки — всегда поверх модалок
      },
      transitionDuration: {
        fast: '120ms',
        base: '200ms',
        slow: '280ms',
      },
    },
  },
  plugins: [],
}
