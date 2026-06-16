import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev-сервер на 5173; api-gateway (CORS разрешает localhost:5173) вызывается напрямую по VITE_API_URL.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
})
