import { useLocation, useNavigate } from 'react-router-dom'
import { Compass, ArrowLeft, LayoutDashboard } from 'lucide-react'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import Button from '../components/Button'

/**
 * Страница 404.
 * Раньше любой неизвестный адрес молча редиректил на /dashboard — пользователь
 * не понимал, что ссылка битая, а история навигации портилась
 * (правила back-stack-integrity / empty-nav-state).
 */
export default function NotFound() {
  useDocumentTitle('Страница не найдена')
  const navigate = useNavigate()
  const { pathname } = useLocation()

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-surface2 text-muted">
        <Compass size={22} aria-hidden="true" />
      </span>
      <div>
        <h1 className="text-lg font-semibold text-ink">Страница не найдена</h1>
        <p className="mt-1 max-w-md text-sm text-muted">
          Адрес <code className="break-all text-ink">{pathname}</code> не существует. Возможно, ссылка
          устарела или в ней опечатка.
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-3">
        <Button onClick={() => navigate(-1)}>
          <ArrowLeft size={15} aria-hidden="true" />
          Назад
        </Button>
        <Button variant="primary" onClick={() => navigate('/dashboard')}>
          <LayoutDashboard size={15} aria-hidden="true" />
          На дашборд
        </Button>
      </div>
    </div>
  )
}
