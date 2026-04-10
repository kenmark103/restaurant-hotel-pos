export type OrderType = 'dine_in' | 'counter' | 'takeaway' | 'room_charge'
export type PaymentMethod = 'cash' | 'mobile_money' | 'card' | 'room_charge'
export type PosOrderStatus = 'open' | 'sent' | 'closed' | 'voided'
export type DiscountType = 'percent' | 'fixed'

export interface OrderDiscount {
  id: number
  order_id: number
  order_item_id: number | null
  discount_type: DiscountType
  value: string
  amount: string
  reason: string | null
}

export interface PosOrderItem {
  id: number
  order_id: number
  menu_item_id: number
  menu_item_name: string
  variant_id: number | null
  variant_name: string | null
  quantity: number
  unit_price: string
  line_total: string
  note: string | null
  is_voided: boolean
  void_reason: string | null
  created_at: string
  updated_at: string
}

export interface PosOrder {
  id: number
  branch_id: number
  table_id: number | null
  staff_user_id: number
  order_type: OrderType
  status: PosOrderStatus
  room_number: string | null
  customer_name: string | null
  note: string | null
  subtotal: string
  tax_amount: string
  discount_total: string
  total_amount: string
  payment_method: PaymentMethod | null
  amount_paid: string | null
  closed_at: string | null
  created_at: string
  updated_at: string
  items: PosOrderItem[]
  discounts: OrderDiscount[]
}

export interface CreateOrderPayload {
  order_type: OrderType
  table_id?: number
  branch_id?: number
  room_number?: string
  customer_name?: string
  note?: string
}

export interface AddOrderItemPayload {
  menu_item_id: number
  variant_id?: number
  quantity: number
  note?: string
}

export interface UpdateOrderItemPayload {
  quantity: number
  note: string | null
}

export interface VoidOrderItemPayload {
  reason?: string
}

export interface CloseOrderPayload {
  payment_method: PaymentMethod
  amount_paid: string
}

export interface ApplyDiscountPayload {
  discount_type: DiscountType
  value: number
  order_item_id?: number
  reason?: string
}
