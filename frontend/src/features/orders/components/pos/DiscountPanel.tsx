/**
 * features/orders/components/pos/DiscountPanel.tsx
 *
 * Inline panel inside the TicketPanel for applying an order-level discount.
 * Supports both percentage and fixed amount.
 * Shown/hidden by a "% Discount" button in the ticket footer.
 */

import { useState } from 'react'
import type { DiscountType, ApplyDiscountPayload } from '@/features/orders/types'

interface DiscountPanelProps {
  orderSubtotal: number
  isBusy: boolean
  formatPrice: (v: number | string) => string
  onApply: (payload: ApplyDiscountPayload) => void
  onClose: () => void
}

export function DiscountPanel({
  orderSubtotal,
  isBusy,
  formatPrice,
  onApply,
  onClose,
}: DiscountPanelProps) {
  const [discountType, setDiscountType] = useState<DiscountType>('percent')
  const [value, setValue] = useState('')
  const [reason, setReason] = useState('')

  const numValue = Number.parseFloat(value)
  const isValid = Number.isFinite(numValue) && numValue > 0 &&
    (discountType === 'fixed' ? numValue <= orderSubtotal : numValue <= 100)

  const previewAmount = isValid
    ? discountType === 'percent'
      ? (orderSubtotal * numValue) / 100
      : numValue
    : 0

  const handleApply = () => {
    if (!isValid) return
    onApply({ discount_type: discountType, value: numValue, reason: reason.trim() || undefined })
  }

  return (
    <div className="rounded-xl border border-accent/30 bg-accent/5 p-3">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs font-bold uppercase tracking-wide text-accent">Apply Discount</p>
        <button type="button" onClick={onClose} className="text-muted hover:text-ink text-xs">
          Cancel
        </button>
      </div>

      {/* type toggle */}
      <div className="mb-2 flex rounded-lg border border-line overflow-hidden">
        {(['percent', 'fixed'] as DiscountType[]).map((type) => (
          <button
            key={type}
            type="button"
            onClick={() => { setDiscountType(type); setValue('') }}
            className={`flex-1 py-1.5 text-xs font-semibold transition ${
              discountType === type
                ? 'bg-accent text-white'
                : 'bg-white text-muted hover:text-ink'
            }`}
          >
            {type === 'percent' ? '% Percent' : 'KES Fixed'}
          </button>
        ))}
      </div>

      {/* value input */}
      <input
        type="number"
        min="0"
        max={discountType === 'percent' ? '100' : String(orderSubtotal)}
        step="0.01"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={discountType === 'percent' ? 'e.g. 10 for 10%' : 'e.g. 50'}
        className="mb-2 w-full rounded-lg border border-line px-3 py-2 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none"
      />

      {/* reason */}
      <input
        type="text"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Reason (optional)"
        className="mb-3 w-full rounded-lg border border-line px-3 py-2 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none"
      />

      {/* preview */}
      {isValid && (
        <p className="mb-2 text-xs text-muted">
          Discount: <span className="font-bold text-danger">−{formatPrice(previewAmount)}</span>
        </p>
      )}

      <button
        type="button"
        disabled={!isValid || isBusy}
        onClick={handleApply}
        className="w-full rounded-xl bg-accent py-2 text-sm font-bold text-white disabled:opacity-50"
      >
        Apply Discount
      </button>
    </div>
  )
}