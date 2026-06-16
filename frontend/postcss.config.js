import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

// Абсолютный путь к tailwind.config.js — чтобы PostCSS находил конфиг
// независимо от текущей рабочей директории запуска Vite.
const dir = dirname(fileURLToPath(import.meta.url))

export default {
  plugins: {
    tailwindcss: { config: join(dir, 'tailwind.config.js') },
    autoprefixer: {},
  },
}
