import { create } from 'zustand'

type Audience = 'staff' | 'customer'

type AuthState = {
  accessToken: string | null
  refreshToken: string | null
  audience: Audience | null
  setSession: (payload: { accessToken: string; refreshToken: string; audience: Audience }) => void
  clearSession: () => void
}

const storageKey = 'restaurant-hotel-pos-auth'

const readInitialState = () => {
  if (typeof window === 'undefined') {
    return { accessToken: null, refreshToken: null, audience: null }
  }

  const stored = window.localStorage.getItem(storageKey)
  if (!stored) {
    return { accessToken: null, refreshToken: null, audience: null }
  }

  try {
    return JSON.parse(stored) as Pick<AuthState, 'accessToken' | 'refreshToken' | 'audience'>
  } catch {
    return { accessToken: null, refreshToken: null, audience: null }
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  ...readInitialState(),
  setSession: ({ accessToken, refreshToken, audience }) =>
    set(() => {
      const nextState = { accessToken, refreshToken, audience }
      window.localStorage.setItem(storageKey, JSON.stringify(nextState))
      return nextState
    }),
  clearSession: () =>
    set(() => {
      window.localStorage.removeItem(storageKey)
      return { accessToken: null, refreshToken: null, audience: null }
    }),
}))
