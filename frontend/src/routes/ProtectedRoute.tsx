import { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

import { useAuthStore } from '../lib/authStore'

export function ProtectedRoute({ audience, children }: { audience: 'staff' | 'customer'; children: ReactNode }) {
  const { accessToken, audience: currentAudience } = useAuthStore()

  if (!accessToken || currentAudience !== audience) {
    return <Navigate to={audience === 'staff' ? '/staff/login' : '/account/login'} replace />
  }

  return <>{children}</>
}
