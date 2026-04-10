import { useEffect } from 'react'
import axios from 'axios'

import { useAuthStore } from '@/store/authStore'

export function useSessionHydration() {
  const { setSession, setHydrated, isHydrated } = useAuthStore()

  useEffect(() => {
    if (isHydrated) {
      return
    }

    const restore = async () => {
      try {
        const refreshResponse = await axios.post('/api/v1/auth/staff/refresh', {}, { withCredentials: true })
        const token: string = refreshResponse.data.access_token
        useAuthStore.getState().setAccessToken(token)

        const meResponse = await axios.get('/api/v1/me', {
          withCredentials: true,
          headers: { Authorization: `Bearer ${token}` },
        })
        setSession(token, meResponse.data)
      } catch {
        useAuthStore.getState().clearSession()
      } finally {
        setHydrated()
      }
    }

    void restore()
  }, [isHydrated, setHydrated, setSession])
}
