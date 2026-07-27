import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev-сервер на 5173. Запросы к API проксируются на api-gateway так же, как это
// делает nginx в контейнере (frontend/nginx.conf) — поэтому фолбэки в
// src/lib/api.ts (`baseURL: '' `) и src/hooks/useWebSocket.ts (origin страницы)
// корректны в ОБОИХ режимах, и переменные VITE_API_URL / VITE_WS_URL не нужны
// ни здесь, ни в проде.
//
// Почему прокси, а не frontend/.env: .gitignore игнорирует `*.env`, поэтому такой
// файл нельзя закоммитить и каждый разработчик создавал бы его вручную. Раньше
// его просто не было — и `npm run dev` бил в сам dev-сервер: POST /api/v1/auth/login
// получал 404, а GET'ы возвращали index.html вместо JSON, без единого тоста.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
  build: {
    // Разносим тяжёлые зависимости по отдельным чанкам: recharts (~350 КБ) грузится
    // параллельно с приложением и кешируется отдельно от кода — при выкладке новой
    // версии UI браузер не перекачивает библиотеки заново.
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          // recharts тянет за собой набор пакетов d3-* — они должны уехать в тот же чанк
          if (/node_modules\/(recharts|d3-|victory-vendor|internmap|delaunator|robust-predicates)/.test(id)) {
            return 'charts'
          }
          if (/node_modules\/(react|react-dom|react-router|react-router-dom|scheduler)\//.test(id)) {
            return 'react-vendor'
          }
          // Остальное оставляем стратегии Vite по умолчанию: попытка вынести
          // «всё прочее» в общий vendor давала циклическую зависимость чанков.
          return undefined
        },
      },
    },
    chunkSizeWarningLimit: 700,
  },
})
