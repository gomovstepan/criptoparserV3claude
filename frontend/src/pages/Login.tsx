import { type FormEvent, useId, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import { toast } from 'sonner'
import { loginRequest } from '../lib/api'
import { useAuthStore } from '../store/authStore'
import Button from '../components/Button'

interface LocationState {
  from?: string
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/**
 * Экран входа.
 *
 * Исправлено: label были не связаны с полями (клик по подписи ничего не делал,
 * скринридер читал поле без имени); ошибки показывались только тостом в углу,
 * а не рядом с полем; у пароля не было переключателя видимости; после
 * авторизации всегда открывался Dashboard, даже если пользователь пришёл
 * по прямой ссылке на другую страницу.
 */
export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const setAuth = useAuthStore((s) => s.setAuth)

  const emailId = useId()
  const passwordId = useId()
  const errorId = useId()
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)

  const [email, setEmail] = useState('test@example.com')
  const [password, setPassword] = useState('test123')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<{ email?: string; password?: string; form?: string }>({})

  const from = (location.state as LocationState | null)?.from ?? '/dashboard'

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const next: typeof errors = {}
    if (!email.trim()) next.email = 'Укажите email'
    else if (!EMAIL_RE.test(email.trim())) next.email = 'Похоже, в адресе опечатка'
    if (!password) next.password = 'Укажите пароль'

    setErrors(next)
    if (next.email) {
      // Фокус на первое поле с ошибкой (правило focus-management)
      emailRef.current?.focus()
      return
    }
    if (next.password) {
      passwordRef.current?.focus()
      return
    }

    setLoading(true)
    try {
      const data = await loginRequest(email.trim(), password)
      setAuth(data.access_token, email.trim())
      toast.success('Вход выполнен')
      navigate(from, { replace: true })
    } catch {
      setErrors({ form: 'Неверный email или пароль. Проверьте данные и попробуйте снова.' })
      passwordRef.current?.focus()
    } finally {
      setLoading(false)
    }
  }

  const fieldClass = (invalid?: string) =>
    `w-full rounded-lg border bg-surface2 px-3 py-2 text-sm text-ink transition-colors duration-fast min-h-[44px] ${
      invalid ? 'border-danger' : 'border-edge-strong focus:border-accent'
    }`

  return (
    <main className="flex min-h-dvh items-center justify-center bg-page px-4 py-8">
      <div className="w-full max-w-sm rounded-2xl border border-edge bg-surface p-6 shadow-2xl sm:p-8">
        <div className="mb-1 flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-accent" aria-hidden="true" />
          <h1 className="text-xl font-semibold text-ink">ArbitrageHub</h1>
        </div>
        <p className="mb-6 text-sm text-muted">Войдите в панель управления</p>

        <form onSubmit={onSubmit} noValidate className="space-y-4">
          {errors.form && (
            <p id={errorId} role="alert" className="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger">
              {errors.form}
            </p>
          )}

          <div>
            <label htmlFor={emailId} className="mb-1 block text-xs font-medium text-muted">
              Email
            </label>
            <input
              id={emailId}
              ref={emailRef}
              type="email"
              inputMode="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value)
                if (errors.email) setErrors((p) => ({ ...p, email: undefined }))
              }}
              autoComplete="username"
              placeholder="you@example.com"
              aria-invalid={errors.email ? true : undefined}
              aria-describedby={errors.email ? `${emailId}-err` : undefined}
              className={fieldClass(errors.email)}
            />
            {errors.email && (
              <p id={`${emailId}-err`} role="alert" className="mt-1 text-xs text-danger">
                {errors.email}
              </p>
            )}
          </div>

          <div>
            <label htmlFor={passwordId} className="mb-1 block text-xs font-medium text-muted">
              Пароль
            </label>
            <div className="relative">
              <input
                id={passwordId}
                ref={passwordRef}
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value)
                  if (errors.password) setErrors((p) => ({ ...p, password: undefined }))
                }}
                autoComplete="current-password"
                placeholder="••••••••"
                aria-invalid={errors.password ? true : undefined}
                aria-describedby={errors.password ? `${passwordId}-err` : undefined}
                className={`${fieldClass(errors.password)} pr-12`}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
                aria-pressed={showPassword}
                className="tap-target absolute right-1 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-lg text-muted transition-colors duration-fast hover:text-ink"
              >
                {showPassword ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
              </button>
            </div>
            {errors.password && (
              <p id={`${passwordId}-err`} role="alert" className="mt-1 text-xs text-danger">
                {errors.password}
              </p>
            )}
          </div>

          <Button type="submit" variant="primary" loading={loading} loadingText="Вход…" className="w-full">
            Войти
          </Button>
        </form>

        <p className="mt-4 text-center text-xs text-muted">demo: test@example.com / test123</p>
      </div>
    </main>
  )
}
