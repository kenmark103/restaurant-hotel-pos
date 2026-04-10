import type { PaymentMethod } from '@/features/orders/types'
import { AppSelect } from '@/shared/ui/AppSelect'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'

interface PaymentSectionProps {
  totalAmount: number
  paymentMethod: PaymentMethod
  amountPaid: string
  changeDue: number
  canClose: boolean
  isWorking: boolean
  formatPrice: (v: number | string) => string
  onMethodChange: (method: PaymentMethod) => void
  onAmountChange: (value: string) => void
  onClose: () => void
}

const PAYMENT_OPTIONS: Array<{ value: PaymentMethod; label: string }> = [
  { value: 'cash', label: 'Cash' },
  { value: 'mobile_money', label: 'Mobile money' },
  { value: 'card', label: 'Card' },
  { value: 'room_charge', label: 'Room charge' },
]

export function PaymentSection({
  totalAmount,
  paymentMethod,
  amountPaid,
  changeDue,
  canClose,
  isWorking,
  formatPrice,
  onMethodChange,
  onAmountChange,
  onClose,
}: PaymentSectionProps) {
  return (
    <div className="space-y-2 rounded-xl border border-line bg-white p-3">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-faint">Close and pay</p>
      <p className="text-xs text-muted">Total: {formatPrice(totalAmount)}</p>
      <AppSelect value={paymentMethod} onChange={(event) => onMethodChange(event.target.value as PaymentMethod)}>
        {PAYMENT_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </AppSelect>
      <Input
        min={0}
        onChange={(event) => onAmountChange(event.target.value)}
        placeholder="Amount paid"
        step="0.01"
        type="number"
        value={amountPaid}
      />

      {paymentMethod === 'cash' && changeDue > 0 ? (
        <p className="text-sm font-semibold text-success-text">Change: {formatPrice(changeDue.toFixed(2))}</p>
      ) : null}

      <Button className="w-full" disabled={!canClose || isWorking} onClick={onClose} type="button">
        Close ticket
      </Button>
    </div>
  )
}
