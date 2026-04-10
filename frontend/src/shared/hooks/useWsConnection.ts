/**
 * useWsConnection.ts
 * Call this once in StaffShell. It connects the WebSocket when a staff user
 * has a branch, and disconnects cleanly on logout or unmount.
 *
 * Usage in StaffShell.tsx:
 *   useWsConnection()
 */

import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { useAuthStore } from '@/store/authStore'
import { useWsStore } from '@/store/wsStore'

export function useWsConnection() {
  const user        = useAuthStore((s) => s.user)
  const accessToken = useAuthStore((s) => s.accessToken)
  const queryClient = useQueryClient()
  const connect     = useWsStore((s) => s.connect)
  const disconnect  = useWsStore((s) => s.disconnect)

  const branchId = user?.branch_id ?? null

  useEffect(() => {
    // Only connect if the user is a scoped staff member with a branch
    if (!branchId || !accessToken) {
      return
    }

    connect(branchId, accessToken, queryClient)

    return () => {
      disconnect()
    }
  }, [branchId, accessToken, connect, disconnect, queryClient])
}