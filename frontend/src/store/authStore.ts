import { create } from 'zustand'

interface AuthState {
  token: string | null
  user: string | null
  setAuth: (token: string, user: string) => void
  logout: () => void
}

/** Состояние аутентификации. Токен и пользователь персистятся в localStorage. */
export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  user: localStorage.getItem('user'),
  setAuth: (token, user) => {
    localStorage.setItem('token', token)
    localStorage.setItem('user', user)
    set({ token, user })
  },
  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ token: null, user: null })
  },
}))
