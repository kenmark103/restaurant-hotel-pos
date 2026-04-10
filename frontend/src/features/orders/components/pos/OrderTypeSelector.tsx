/**
 * features/orders/components/pos/OrderTypeSelector.tsx
 *
 * Shown when creating a non-table order (counter, takeaway, room charge).
 * Sits as a modal/drawer above the POS terminal.
 */

import { useState } from 'react'
import type { CreateOrderPayload, OrderType } from '@/features/orders/types'

interface OrderTypeSelectorProps {
  branchId: number
  isBusy: boolean
  onConfirm: (payload: CreateOrderPayload) => void
  onClose: () => void
}

const ORDER_TYPES: Array<{ type: OrderType; label: string; icon: string; requiresInput: boolean }> = [
  { type: 'counter',     label: 'Counter',      icon: '🛒', requiresInput: false },
  { type: 'takeaway',    label: 'Takeaway',      icon: '📦', requiresInput: true  },
  { type: 'room_charge', label: 'Room Charge',   icon: '🛏️',  requiresInput: true  },
]

export function OrderTypeSelector({
  branchId,
  isBusy,
  onConfirm,
  onClose,
}: OrderTypeSelectorProps) {
  const [selectedType, setSelectedType] = useState<OrderType>('counter')
  const [customerName, setCustomerName] = useState('')
  const [roomNumber, setRoomNumber]     = useState('')

  const selected = ORDER_TYPES.find((t) => t.type === selectedType)!

  const handleConfirm = () => {
    onConfirm({
      order_type: selectedType,
      branch_id: branchId,
      customer_name: customerName.trim() || undefined,
      room_number: roomNumber.trim() || undefined,
    })
  }

  const isValid =
    selectedType === 'counter' ||
    (selectedType === 'takeaway' && customerName.trim().length > 0) ||
    (selectedType === 'room_charge' && roomNumber.trim().length > 0)

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="mb-4 text-base font-bold text-ink">New Order</p>

        {/* Order type selector */}
        <div className="mb-4 flex gap-2">
          {ORDER_TYPES.map(({ type, label, icon }) => (
            <button
              key={type}
              type="button"
              onClick={() => setSelectedType(type)}
              className={`flex flex-1 flex-col items-center gap-1 rounded-xl border py-3 text-xs font-semibold transition ${
                selectedType === type
                  ? 'border-accent bg-accent/10 text-accent'
                  : 'border-line bg-white text-muted hover:border-accent/40'
              }`}
            >
              <span className="text-xl">{icon}</span>
              {label}
            </button>
          ))}
        </div>

        {/* Contextual input */}
        {selectedType === 'takeaway' && (
          <div className="mb-4">
            <label className="app-label mb-1 block">Customer Name *</label>
            <input
              autoFocus
              type="text"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              placeholder="e.g. John"
              className="w-full rounded-xl border border-line px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none"
            />
          </div>
        )}

        {selectedType === 'room_charge' && (
          <div className="mb-4">
            <label className="app-label mb-1 block">Room Number *</label>
            <input
              autoFocus
              type="text"
              value={roomNumber}
              onChange={(e) => setRoomNumber(e.target.value)}
              placeholder="e.g. 204"
              className="w-full rounded-xl border border-line px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none"
            />
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-xl border border-line py-2.5 text-sm font-semibold text-muted"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!isValid || isBusy}
            onClick={handleConfirm}
            className="flex-1 rounded-xl bg-accent py-2.5 text-sm font-bold text-white disabled:opacity-50"
          >
            Open Ticket
          </button>
        </div>
      </div>
    </div>
  )
}