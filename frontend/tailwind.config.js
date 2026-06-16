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
        accent: 'rgb(var(--c-accent) / <alpha-value>)',
        success: 'rgb(var(--c-success) / <alpha-value>)',
        danger: 'rgb(var(--c-danger) / <alpha-value>)',
        warning: 'rgb(var(--c-warning) / <alpha-value>)',
        ink: 'rgb(var(--c-ink) / <alpha-value>)',
        muted: 'rgb(var(--c-muted) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
