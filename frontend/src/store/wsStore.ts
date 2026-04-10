/**
 * wsStore.ts
 * Zustand store that owns the WebSocket connection lifecycle.
 *
 * Usage:
 *   const { connect, disconnect, isConnected } = useWsStore()
 *
 * Call connect(branchId) once after login (e.g. in StaffShell or useSessionHydration).
 * The store dispatches events into React Query's cache so all queries
 * stay fresh without polling.
 *
 * Backend expects: ws://{host}/api/v1/ws/branch/{branchId}?token={accessToken}
 *
 * Event envelope from server:
 *   { type: 'order.sent' | 'order.closed' | 'order.voided' | 'table.status', payload: {...} }
 */

import { create } from 'zustand'
import { QueryClient } from '@tanstack/react-query'

// ─── Event types (mirror your backend WS events) ──────────────────────────────

export type WsEvent =
  | { type: 'order.sent';    payload: { order_id: number; branch_id: number } }
  | { type: 'order.closed';  payload: { order_id: number; branch_id: number } }
  | { type: 'order.voided';  payload: { order_id: number; branch_id: number } }
  | { type: 'order.updated'; payload: { order_id: number; branch_id: number } }
  | { type: 'table.status';  payload: { table_id: number; branch_id: number; status: string } }

// ─── Store interface ──────────────────────────────────────────────────────────

interface WsState {
  socket:      WebSocket | null
  branchId:    number | null
  isConnected: boolean
  reconnectCount: number

  connect:    (branchId: number, accessToken: string, queryClient: QueryClient) => void
  disconnect: () => void
}

const WS_BASE = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'
const MAX_RECONNECTS = 5
const RECONNECT_DELAY_MS = 3000

export const useWsStore = create<WsState>((set, get) => ({
  socket:         null,
  branchId:       null,
  isConnected:    false,
  reconnectCount: 0,

  connect(branchId, accessToken, queryClient) {
    const { socket: existing, disconnect } = get()

    // Already connected to this branch — skip
    if (existing && get().branchId === branchId && existing.readyState === WebSocket.OPEN) {
      return
    }

    // Clean up previous socket
    disconnect()

    const url = `${WS_BASE}/api/v1/ws/branch/${branchId}?token=${accessToken}`
    const ws = new WebSocket(url)

    ws.onopen = () => {
      set({ isConnected: true, reconnectCount: 0 })
      console.debug('[WS] Connected — branch', branchId)
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string) as WsEvent
        handleWsEvent(msg, branchId, queryClient)
      } catch {
        // non-JSON frame — ignore
      }
    }

    ws.onclose = (event) => {
      set({ isConnected: false, socket: null })
      console.debug('[WS] Closed', event.code, event.reason)

      const { reconnectCount } = get()
      if (reconnectCount < MAX_RECONNECTS && event.code !== 1000) {
        // 1000 = clean close (logout), no reconnect
        setTimeout(() => {
          set((s) => ({ reconnectCount: s.reconnectCount + 1 }))
          get().connect(branchId, accessToken, queryClient)
        }, RECONNECT_DELAY_MS * (reconnectCount + 1))
      }
    }

    ws.onerror = (err) => {
      console.error('[WS] Error', err)
    }

    set({ socket: ws, branchId })
  },

  disconnect() {
    const { socket } = get()
    if (socket) {
      socket.close(1000, 'clean disconnect')
    }
    set({ socket: null, isConnected: false, branchId: null, reconnectCount: 0 })
  },
}))

// ─── Event → React Query cache invalidation ───────────────────────────────────

function handleWsEvent(event: WsEvent, branchId: number, queryClient: QueryClient) {
  switch (event.type) {
    case 'order.sent':
    case 'order.closed':
    case 'order.voided':
    case 'order.updated':
      // Invalidate active orders list and the specific order detail
      queryClient.invalidateQueries({ queryKey: ['orders', 'active', branchId] })
      queryClient.invalidateQueries({ queryKey: ['orders', 'detail', event.payload.order_id] })
      break

    case 'table.status':
      // Invalidate the tables list for this branch
      queryClient.invalidateQueries({ queryKey: ['tables', branchId] })
      break
  }
}