import { useQuery } from '@tanstack/react-query'

import { apiClient } from '@/shared/api/client'
import { useAuthStore } from '@/store/authStore'

export function useCurrentUser() {
  const accessToken = useAuthStore((state) => state.accessToken)

  return useQuery({
    queryKey: ['current-user'],
    queryFn: async () => {
      const response = await apiClient.get('/me')
      return response.data
    },
    enabled: Boolean(accessToken),
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}
