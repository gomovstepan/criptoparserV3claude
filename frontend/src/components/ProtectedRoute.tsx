import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

/**
 * Пускает дальше только при наличии токена, иначе — редирект на /login.
 * Запрошенный адрес передаётся в state, чтобы после входа вернуть пользователя
 * именно туда, куда он шёл (правило deep-linking / back-behavior).
 */
export default function ProtectedRoute() {
  const token = useAuthStore((s) => s.token)
  const location = useLocation()

  if (token) return <Outlet />
  return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
}
