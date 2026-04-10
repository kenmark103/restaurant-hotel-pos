import { create } from 'zustand'

export interface AuthUser {
  id: number
  email: string
  full_name: string
  user_type: 'staff' | 'customer'
  role?: string
  staff_status?: string
  branch_id?: number | null
  loyalty_points?: number | null
}

interface AuthState {
  accessToken: string | null
  user: AuthUser | null
  isHydrated: boolean
  setSession: (token: string, user: AuthUser) => void
  setAccessToken: (token: string) => void
  clearSession: () => void
  setHydrated: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  isHydrated: false,
  setSession: (token, user) => set({ accessToken: token, user }),
  setAccessToken: (token) => set({ accessToken: token }),
  clearSession: () => set({ accessToken: null, user: null }),
  setHydrated: () => set({ isHydrated: true }),
}))
