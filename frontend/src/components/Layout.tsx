import { Suspense, useEffect, useRef, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import Navbar from './Navbar'
import NetworkStatus from './NetworkStatus'
import ErrorBoundary from './ErrorBoundary'
import { SkeletonCards } from './LoadingSkeleton'
import { useWebSocket } from '../hooks/useWebSocket'

/** Заглушка на время подгрузки чанка страницы: каркас приложения остаётся на месте. */
function PageFallback() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 animate-pulse rounded bg-surface2" />
      <SkeletonCards count={4} />
    </div>
  )
}

/** Каркас приложения: Sidebar слева, Navbar сверху, контент через Outlet.
 *  Здесь же — единое WS-подключение, живущее на всех защищённых страницах,
 *  баннер статуса сети и error boundary вокруг страниц. */
export default function Layout() {
  useWebSocket()
  const [mobileOpen, setMobileOpen] = useState(false)
  const { pathname } = useLocation()
  const mainRef = useRef<HTMLElement>(null)
  const firstRender = useRef(true)

  // После смены маршрута фокус переносится в основную область: иначе он остаётся
  // на пункте меню, и скринридер не сообщает о смене страницы (focus-on-route-change).
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false
      return
    }
    mainRef.current?.focus()
    mainRef.current?.scrollTo({ top: 0 })
  }, [pathname])

  return (
    // h-dvh вместо h-screen: на мобильных 100vh не учитывает адресную строку
    <div className="flex h-dvh bg-page">
      <a href="#main" className="skip-link">
        Перейти к содержимому
      </a>
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Navbar onMenuClick={() => setMobileOpen(true)} />
        <NetworkStatus />
        <main
          id="main"
          ref={mainRef}
          tabIndex={-1}
          className="flex-1 overflow-auto p-4 outline-none sm:p-6"
        >
          {/* key: краш одной страницы не должен «кирпичить» остальные —
              смена маршрута пересоздаёт boundary и сбрасывает ошибку. */}
          <ErrorBoundary key={pathname}>
            <Suspense fallback={<PageFallback />}>
              <Outlet />
            </Suspense>
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
