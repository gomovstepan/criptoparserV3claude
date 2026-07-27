import { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import ErrorBoundary from './components/ErrorBoundary'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import { useThemeStore } from './store/themeStore'

// Разделение бандла по маршрутам: recharts и страницы аналитики/сделок больше
// не тянутся при первом заходе. Dashboard остаётся в основном чанке — это
// стартовый экран, и отдельный запрос за ним только задержал бы первую отрисовку.
const Opportunities = lazy(() => import('./pages/Opportunities'))
const Trades = lazy(() => import('./pages/Trades'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Exchanges = lazy(() => import('./pages/Exchanges'))
const Settings = lazy(() => import('./pages/Settings'))
const NotFound = lazy(() => import('./pages/NotFound'))

export default function App() {
  const theme = useThemeStore((s) => s.theme)
  return (
    <ErrorBoundary>
      {/* Внутренний Suspense живёт в Layout и сохраняет каркас приложения;
          этот — страховка для маршрутов вне Layout. */}
      <Suspense fallback={<div className="min-h-dvh bg-page" />}>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/opportunities" element={<Opportunities />} />
              <Route path="/trades" element={<Trades />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/exchanges" element={<Exchanges />} />
              <Route path="/settings" element={<Settings />} />
              {/* 404 внутри Layout: навигация остаётся доступной (persistent-nav) */}
              <Route path="*" element={<NotFound />} />
            </Route>
          </Route>

          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
      <Toaster theme={theme} position="top-right" richColors closeButton duration={5000} />
    </ErrorBoundary>
  )
}
