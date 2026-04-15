import { create } from "zustand";
import type { OrderRead, OrderItemRead, PaymentMethod } from "@restaurantos/api";

interface CartItem extends OrderItemRead {
  // optimistic-only fields (cleared on server confirm)
  _optimistic?: boolean;
  _tempId?: string;
}

interface CartState {
  // ── Data ────────────────────────────────────────────────────────────────
  orderId: number | null;
  orderType: string | null;
  tableId: number | null;
  tableNumber: string | null;
  items: CartItem[];
  subtotal: string;
  taxAmount: string;
  discountTotal: string;
  totalAmount: string;
  status: string | null;

  // ── Actions ──────────────────────────────────────────────────────────────
  hydrateFromOrder: (order: OrderRead) => void;
  addItemOptimistic: (item: CartItem) => void;
  removeItemOptimistic: (itemId: number) => void;
  voidItemOptimistic: (itemId: number) => void;
  clearCart: () => void;
  setOrderId: (id: number) => void;
}

const EMPTY: Pick<CartState,
  "orderId" | "orderType" | "tableId" | "tableNumber" |
  "items" | "subtotal" | "taxAmount" | "discountTotal" |
  "totalAmount" | "status"
> = {
  orderId: null,
  orderType: null,
  tableId: null,
  tableNumber: null,
  items: [],
  subtotal: "0.00",
  taxAmount: "0.00",
  discountTotal: "0.00",
  totalAmount: "0.00",
  status: null,
};

export const useCartStore = create<CartState>((set) => ({
  ...EMPTY,

  hydrateFromOrder: (order) => {
    set({
      orderId: order.id,
      orderType: order.order_type,
      tableId: order.table?.id ?? null,
      tableNumber: order.table?.table_number ?? null,
      items: order.items as CartItem[],
      subtotal: order.subtotal,
      taxAmount: order.tax_amount,
      discountTotal: order.discount_total,
      totalAmount: order.total_amount,
      status: order.status,
    });
  },

  addItemOptimistic: (item) => {
    set((s) => ({ items: [...s.items, item] }));
  },

  removeItemOptimistic: (itemId) => {
    set((s) => ({ items: s.items.filter((i) => i.id !== itemId) }));
  },

  voidItemOptimistic: (itemId) => {
    set((s) => ({
      items: s.items.map((i) =>
        i.id === itemId ? { ...i, is_voided: true } : i
      ),
    }));
  },

  setOrderId: (id) => set({ orderId: id }),

  clearCart: () => set(EMPTY),
}));