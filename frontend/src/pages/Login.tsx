import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { loginRequest } from '../lib/api'
import { useAuthStore } from '../store/authStore'

export default function Login() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [email, setEmail] = useState('test@example.com')
  const [password, setPassword] = useState('test123')
  const [loading, setLoading] = useState(false)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!email || !password) {
      toast.error('Введите email и пароль')
      return
    }
    setLoading(true)
    try {
      const data = await loginRequest(email, password)
      setAuth(data.access_token, email)
      toast.success('Вход выполнен')
      navigate('/dashboard')
    } catch {
      toast.error('Неверные учётные данные')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-page px-4">
      <div className="w-full max-w-sm rounded-2xl border border-edge bg-surface p-8 shadow-2xl">
        <div className="mb-1 flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-accent" />
          <h1 className="text-xl font-semibold text-ink">ArbitrageHub</h1>
        </div>
        <p className="mb-6 text-sm text-muted">Войдите в панель управления</p>

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs text-muted">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              placeholder="you@example.com"
              className="w-full rounded-lg border border-edge bg-surface2 px-3 py-2 text-sm text-ink outline-none transition-colors focus:border-accent"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted">Пароль</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="••••••••"
              className="w-full rounded-lg border border-edge bg-surface2 px-3 py-2 text-sm text-ink outline-none transition-colors focus:border-accent"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-accent py-2 text-sm font-semibold text-page transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {loading ? 'Вход…' : 'Войти'}
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-muted">demo: test@example.com / test123</p>
      </div>
    </div>
  )
}
