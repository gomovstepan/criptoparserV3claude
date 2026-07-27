import axios from 'axios'
import { toast } from 'sonner'
import { useAuthStore } from '../store/authStore'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
})

// JWT в каждый запрос
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Единая обработка ошибок: 401 → logout, 5xx → toast, network → toast.
// Toast'ы с фиксированными id, чтобы при поллинге не плодить дубли.
api.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error.response?.status
    if (status === 401) {
      useAuthStore.getState().logout()
      if (window.location.pathname !== '/login') window.location.assign('/login')
    } else if (status >= 500) {
      toast.error('Ошибка сервера. Попробуйте позже.', { id: 'server-error' })
    } else if (error.response === undefined && error.code !== 'ERR_CANCELED') {
      toast.error('Нет связи с сервером', { id: 'network-error' })
    }
    return Promise.reject(error)
  },
)

/**
 * Разобрать 422-ответ FastAPI (Pydantic) в карту `поле → сообщение по-русски`.
 * Формат detail: [{loc: ["body", "max_position_pct"], msg, type}, ...].
 * Пустой объект — если это не 422 или формат не совпал (тогда показывать
 * обычный тост об ошибке).
 */
export function parseValidationErrors(err: unknown): Record<string, string> {
  if (!axios.isAxiosError(err) || err.response?.status !== 422) return {}
  const detail: unknown = err.response.data?.detail
  if (!Array.isArray(detail)) return {}
  const messages: Record<string, string> = {
    greater_than_equal: 'Значение меньше допустимого',
    less_than_equal: 'Значение больше допустимого',
    extra_forbidden: 'Неизвестный параметр',
  }
  const out: Record<string, string> = {}
  for (const item of detail) {
    const loc = Array.isArray(item?.loc) ? item.loc : []
    const key = String(loc[loc.length - 1] ?? '')
    if (key) out[key] = messages[String(item?.type)] ?? 'Недопустимое значение'
  }
  return out
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export async function loginRequest(email: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/api/v1/auth/login', { email, password })
  return data
}

export default api
