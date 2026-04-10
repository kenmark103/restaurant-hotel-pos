import { useMemo, useState } from 'react'

import { useSettings } from '@/contexts/SettingsContext'
import { KdsView } from '@/features/orders/components/queue/KdsView'
import { OrderCard } from '@/features/orders/components/queue/OrderCard'
import { OrderDetail } from '@/features/orders/components/queue/OrderDetail'
import { useActiveOrders, useAllOrders, useHoldOrder, useOrderDetail, useSendOrder, useVoidOrder } from '@/features/orders/hooks/useOrders'
import type { PosOrder, PosOrderItem } from '@/features/orders/types'
import { useBranches } from '@/features/staff/hooks/useBranches'
import { useAuthStore } from '@/store/authStore'
import { EmptyState } from '@/shared/ui/EmptyState'
import { Spinner } from '@/shared/ui/Spinner'

type StatusFilter = 'active' | 'open' | 'sent' | 'closed' | 'voided'
type ViewMode = 'queue' | 'kds'

const STATUS_FILTER_LABELS: Record<StatusFilter, string> = {
  active: 'Active',
  open: 'Open',
  sent: 'Sent to kitchen',
  closed: 'Closed',
  voided: 'Voided',
}

export function OrdersPage() {
  const user = useAuthStore((s) => s.user)
  const { formatPrice } = useSettings()

  const { data: branches } = useBranches()
  const [selectedBranchId, setSelectedBranchId] = useState<number | null>(user?.branch_id ?? null)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('active')
  const [viewMode, setViewMode] = useState<ViewMode>('queue')
  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null)

  const { data: activeOrders, isLoading: activeLoading } = useActiveOrders(selectedBranchId)
  const { data: allOrders, isLoading: allLoading } = useAllOrders(selectedBranchId)
  const { data: selectedOrder } = useOrderDetail(selectedOrderId)

  const sendMutation = useSendOrder(selectedBranchId)
  const holdMutation = useHoldOrder(selectedBranchId)
  const voidMutation = useVoidOrder(selectedBranchId)

  const branchOptions = branches ?? []

  const listSource = statusFilter === 'closed' || statusFilter === 'voided' ? allOrders ?? [] : activeOrders ?? []

  const filteredOrders = useMemo(() => {
    if (statusFilter === 'active') {
      return activeOrders ?? []
    }
    return listSource.filter((o) => o.status === statusFilter)
  }, [activeOrders, listSource, statusFilter])

  const kdsByStation = useMemo(() => {
    const sent = activeOrders?.filter((o) => o.status === 'sent') ?? []
    const map = new Map<string, Array<{ order: PosOrder; item: PosOrderItem }>>()

    sent.forEach((order) => {
      order.items
        .filter((item) => !item.is_voided)
        .forEach((item) => {
          const station = (item as PosOrderItem & { station?: string }).station ?? 'any'
          if (!map.has(station)) {
            map.set(station, [])
          }
          map.get(station)?.push({ order, item })
        })
    })

    return map
  }, [activeOrders])

  const counts = useMemo(
    () => ({
      active: activeOrders?.length ?? 0,
      open: activeOrders?.filter((o) => o.status === 'open').length ?? 0,
      sent: activeOrders?.filter((o) => o.status === 'sent').length ?? 0,
      closed: allOrders?.filter((o) => o.status === 'closed').length ?? 0,
      voided: allOrders?.filter((o) => o.status === 'voided').length ?? 0,
    }),
    [activeOrders, allOrders],
  )

  const handleVoid = async (orderId: number) => {
    await voidMutation.mutateAsync({ orderId, payload: { reason: 'Voided from orders queue.' } })
    if (selectedOrderId === orderId) {
      setSelectedOrderId(null)
    }
  }

  if (activeLoading || allLoading) {
    return (
      <div className="app-panel p-8">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="app-panel shrink-0 p-4">
        <div className="flex flex-wrap items-center gap-3">
          {!user?.branch_id && (
            <select
              className="rounded-xl border border-line bg-white px-3 py-2 text-sm text-ink"
              value={selectedBranchId ?? ''}
              onChange={(e) => {
                setSelectedBranchId(e.target.value ? Number(e.target.value) : null)
                setSelectedOrderId(null)
              }}
            >
              <option value="">All branches</option>
              {branchOptions.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          )}

          <div className="flex items-center gap-1 rounded-xl border border-line bg-appbg p-1">
            {(Object.keys(STATUS_FILTER_LABELS) as StatusFilter[]).map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setStatusFilter(f)}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  statusFilter === f ? 'bg-accent text-white' : 'text-muted hover:bg-panel hover:text-ink'
                }`}
              >
                {STATUS_FILTER_LABELS[f]}
                {counts[f] > 0 && <span className="ml-1.5 rounded-full bg-white/20 px-1.5 text-[10px]">{counts[f]}</span>}
              </button>
            ))}
          </div>

          <div className="ml-auto flex items-center gap-1 rounded-xl border border-line bg-appbg p-1">
            <button
              type="button"
              onClick={() => setViewMode('queue')}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                viewMode === 'queue' ? 'bg-accent text-white' : 'text-muted hover:text-ink'
              }`}
            >
              Queue
            </button>
            <button
              type="button"
              onClick={() => setViewMode('kds')}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                viewMode === 'kds' ? 'bg-accent text-white' : 'text-muted hover:text-ink'
              }`}
            >
              KDS feed
            </button>
          </div>
        </div>
      </div>

      {viewMode === 'queue' ? (
        <div className="grid min-h-0 flex-1 gap-3 md:grid-cols-[1fr_380px]">
          <div className="app-panel min-h-0 overflow-y-auto p-3">
            {filteredOrders.length === 0 ? (
              <EmptyState title="No orders" description="No orders match this filter right now." />
            ) : (
              <div className="space-y-2">
                {filteredOrders.map((order) => (
                  <OrderCard
                    key={order.id}
                    order={order}
                    isSelected={order.id === selectedOrderId}
                    formatPrice={formatPrice}
                    onClick={() => setSelectedOrderId(order.id === selectedOrderId ? null : order.id)}
                  />
                ))}
              </div>
            )}
          </div>

          <div className="app-panel min-h-0 overflow-y-auto p-4">
            {!selectedOrder ? (
              <EmptyState title="Select an order" description="Click any order to see its full details and actions." />
            ) : (
              <OrderDetail
                order={selectedOrder}
                formatPrice={formatPrice}
                isWorking={sendMutation.isPending || holdMutation.isPending || voidMutation.isPending}
                onSend={() => void sendMutation.mutateAsync(selectedOrder.id)}
                onHold={() => void holdMutation.mutateAsync(selectedOrder.id)}
                onVoid={() => void handleVoid(selectedOrder.id)}
              />
            )}
          </div>
        </div>
      ) : (
        <KdsView kdsByStation={kdsByStation} formatPrice={formatPrice} />
      )}
    </div>
  )
}
