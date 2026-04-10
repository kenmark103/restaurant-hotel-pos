import { Button } from '@/shared/ui/Button'
import { EmptyState } from '@/shared/ui/EmptyState'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { PaymentSection } from './PaymentSection'
import { TicketLineItem } from './TicketLineItem'
import type { PaymentMethod, PosOrder, PosOrderItem } from '@/features/orders/types'

interface TicketPanelProps {
  className?: string
  activeOrder: PosOrder | null
  ticketItems: PosOrderItem[]
  paymentMethod: PaymentMethod
  amountPaid: string
  changeDue: number
  canClose: boolean
  isWorking: boolean
  formatPrice: (v: number | string) => string
  onSendOrHold: () => void
  onVoidOrder: () => void
  onCloseOrder: () => void
  onAmountChange: (value: string) => void
  onMethodChange: (method: PaymentMethod) => void
  onItemIncrement: (item: PosOrderItem) => void
  onItemDecrement: (item: PosOrderItem) => void
  onItemVoid: (item: PosOrderItem) => void
  onItemPointerDown: (item: PosOrderItem) => void
  onItemPointerUp: () => void
  onItemPointerLeave: () => void
}

export function TicketPanel({
  className = '',
  activeOrder,
  ticketItems,
  paymentMethod,
  amountPaid,
  changeDue,
  canClose,
  isWorking,
  formatPrice,
  onSendOrHold,
  onVoidOrder,
  onCloseOrder,
  onAmountChange,
  onMethodChange,
  onItemIncrement,
  onItemDecrement,
  onItemVoid,
  onItemPointerDown,
  onItemPointerUp,
  onItemPointerLeave,
}: TicketPanelProps) {
  return (
    <section className={`flex min-h-0 flex-col rounded-xl border border-line bg-panel ${className}`}>
      <div className="mb-2 flex items-center justify-between border-b border-line px-3 py-2.5">
        <p className="text-sm font-semibold text-ink">Ticket</p>
        {activeOrder ? <StatusBadge label={activeOrder.status} tone={orderTone(activeOrder.status)} /> : null}
      </div>

      <div className="flex min-h-0 flex-1 flex-col p-3 pt-0">
        {!activeOrder ? (
          <EmptyState
            title="No active ticket"
            description="Open or select a table ticket to start adding items and manage ticket status."
          />
        ) : (
          <div className="flex min-h-0 h-full flex-col">
            <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
              {ticketItems.length === 0 ? (
                <EmptyState title="No line items yet" description="Add menu items from the center panel to build this ticket." />
              ) : (
                ticketItems.map((item) => (
                  <TicketLineItem
                    key={item.id}
                    item={item}
                    isWorking={isWorking}
                    isOrderOpen={activeOrder.status === 'open'}
                    formatPrice={formatPrice}
                    onIncrement={onItemIncrement}
                    onDecrement={onItemDecrement}
                    onVoid={onItemVoid}
                    onPointerDown={onItemPointerDown}
                    onPointerUp={onItemPointerUp}
                    onPointerLeave={onItemPointerLeave}
                  />
                ))
              )}
            </div>

            <div className="mt-3 shrink-0 space-y-3 border-t border-line pt-3">
              <div className="space-y-1 rounded-xl border border-line bg-white p-3">
                <TicketRow label="Subtotal" value={formatPrice(activeOrder.subtotal)} />
                <TicketRow label="Tax" value={formatPrice(activeOrder.tax_amount)} />
                <TicketRow label="Total" value={formatPrice(activeOrder.total_amount)} isStrong />
              </div>

              <Button
                className="w-full"
                disabled={isWorking || ticketItems.length === 0 || (activeOrder.status !== 'open' && activeOrder.status !== 'sent')}
                onClick={onSendOrHold}
                type="button"
              >
                {activeOrder.status === 'sent' ? 'Move to hold' : 'Send to kitchen'}
              </Button>

              <button
                className="w-full rounded-xl border border-danger/30 bg-danger/5 px-3 py-2.5 text-sm font-semibold text-danger disabled:opacity-50"
                disabled={isWorking || (activeOrder.status !== 'open' && activeOrder.status !== 'sent')}
                onClick={onVoidOrder}
                type="button"
              >
                Void ticket
              </button>

              <PaymentSection
                totalAmount={Number(activeOrder.total_amount)}
                paymentMethod={paymentMethod}
                amountPaid={amountPaid}
                changeDue={changeDue}
                canClose={canClose}
                isWorking={isWorking}
                formatPrice={formatPrice}
                onMethodChange={onMethodChange}
                onAmountChange={onAmountChange}
                onClose={onCloseOrder}
              />
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

function TicketRow({ label, value, isStrong = false }: { label: string; value: string; isStrong?: boolean }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className={isStrong ? 'font-semibold text-ink' : 'text-muted'}>{label}</span>
      <span className={isStrong ? 'font-semibold text-ink' : 'text-ink'}>{value}</span>
    </div>
  )
}

function orderTone(status: PosOrder['status']): 'neutral' | 'info' | 'success' | 'warning' | 'danger' {
  if (status === 'open') {
    return 'warning'
  }
  if (status === 'sent') {
    return 'info'
  }
  if (status === 'closed') {
    return 'success'
  }
  if (status === 'voided') {
    return 'danger'
  }
  return 'neutral'
}
