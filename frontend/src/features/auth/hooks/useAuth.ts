import { useMutation, useQueryClient } from '@tanstack/react-query'

import { authApi } from '@/features/auth/api/authApi'
import { useAuthStore } from '@/store/authStore'

export function useStaffLogin() {
  const setSession = useAuthStore((state) => state.setSession)
  const setAccessToken = useAuthStore((state) => state.setAccessToken)
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: authApi.loginStaff,
    onSuccess: async (data) => {
      setAccessToken(data.access_token)
      const user = await authApi.getCurrentUser()
      setSession(data.access_token, user)
      queryClient.setQueryData(['current-user'], user)
    },
  })
}

export function useLogout() {
  const clearSession = useAuthStore((state) => state.clearSession)
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      clearSession()
      queryClient.removeQueries({ queryKey: ['current-user'] })
    },
  })
}
