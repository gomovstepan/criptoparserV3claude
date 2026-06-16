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
