import { apiClient } from "../src/client";
import type { components } from "@restaurantos/schemas";

type OrderRead = components["schemas"]["OrderRead"];
type CreateOrderRequest = components["schemas"]["CreateOrderRequest"];
type AddOrderItemRequest = components["schemas"]["AddOrderItemRequest"];
type SendToKitchenRequest = components["schemas"]["SendToKitchenRequest"];
type CloseOrderRequest = components["schemas"]["CloseOrderRequest"];
type VoidOrderRequest = components["schemas"]["VoidOrderRequest"];
type VoidItemRequest = components["schemas"]["VoidItemRequest"];
type ApplyDiscountRequest = components["schemas"]["ApplyDiscountRequest"];
type UpdateQuantityRequest = components["schemas"]["UpdateQuantityRequest"];
type SplitBillRequest = components["schemas"]["SplitBillRequest"];
type MergeTablesRequest = components["schemas"]["MergeTablesRequest"];
type TableRead = components["schemas"]["TableRead"];
type CreateTableRequest = components["schemas"]["CreateTableRequest"];
type UpdateTableStatusRequest =
  components["schemas"]["UpdateTableStatusRequest"];
type OpenSessionRequest = components["schemas"]["OpenSessionRequest"];
type CloseSessionRequest = components["schemas"]["CloseSessionRequest"];
type CashTransactionRequest = components["schemas"]["CashTransactionRequest"];
type ManagerOverrideRequest = components["schemas"]["ManagerOverrideRequest"];
type CreateReservationRequest =
  components["schemas"]["CreateReservationRequest"];
type UpdateReservationStatusRequest =
  components["schemas"]["UpdateReservationStatusRequest"];
type BulkSyncRequest = components["schemas"]["BulkSyncRequest"];

export const posApi = {
  // ── Orders ──────────────────────────────────────────────────────────────
  listOrders: (params: {
    branch_id: number;
    status?: string;
    limit?: number;
    offset?: number;
  }) =>
    apiClient
      .get<OrderRead[]>("/api/v1/pos/orders", { params })
      .then((r) => r.data),

  getOrder: (orderId: number) =>
    apiClient
      .get<OrderRead>(`/api/v1/pos/orders/${orderId}`)
      .then((r) => r.data),

  createOrder: (body: CreateOrderRequest) =>
    apiClient
      .post<OrderRead>("/api/v1/pos/orders", body)
      .then((r) => r.data),

  addItem: (orderId: number, body: AddOrderItemRequest) =>
    apiClient
      .post<OrderRead>(`/api/v1/pos/orders/${orderId}/items`, body)
      .then((r) => r.data),

  updateItemQuantity: (
    orderId: number,
    itemId: number,
    body: UpdateQuantityRequest
  ) =>
    apiClient
      .patch<OrderRead>(
        `/api/v1/pos/orders/${orderId}/items/${itemId}/quantity`,
        body
      )
      .then((r) => r.data),

  voidItem: (orderId: number, itemId: number, body: VoidItemRequest) =>
    apiClient
      .delete<OrderRead>(
        `/api/v1/pos/orders/${orderId}/items/${itemId}`,
        { data: body }
      )
      .then((r) => r.data),

  sendToKitchen: (orderId: number, body: SendToKitchenRequest = {}) =>
    apiClient
      .post<OrderRead>(`/api/v1/pos/orders/${orderId}/send`, body)
      .then((r) => r.data),

  closeOrder: (orderId: number, body: CloseOrderRequest) =>
    apiClient
      .post<OrderRead>(`/api/v1/pos/orders/${orderId}/close`, body)
      .then((r) => r.data),

  voidOrder: (orderId: number, body: VoidOrderRequest) =>
    apiClient
      .post<OrderRead>(`/api/v1/pos/orders/${orderId}/void`, body)
      .then((r) => r.data),

  applyDiscount: (orderId: number, body: ApplyDiscountRequest) =>
    apiClient
      .post<OrderRead>(`/api/v1/pos/orders/${orderId}/discounts`, body)
      .then((r) => r.data),

  removeDiscount: (orderId: number, discountId: number) =>
    apiClient
      .delete<OrderRead>(
        `/api/v1/pos/orders/${orderId}/discounts/${discountId}`
      )
      .then((r) => r.data),

  splitBill: (orderId: number, body: SplitBillRequest) =>
    apiClient
      .post<OrderRead[]>(`/api/v1/pos/orders/${orderId}/split`, body)
      .then((r) => r.data),

  mergeTables: (body: MergeTablesRequest) =>
    apiClient
      .post<OrderRead>("/api/v1/pos/orders/merge-tables", body)
      .then((r) => r.data),

  bulkSync: (body: BulkSyncRequest) =>
    apiClient
      .post<unknown[]>("/api/v1/pos/orders/bulk-sync", body)
      .then((r) => r.data),

  // ── Tables ───────────────────────────────────────────────────────────────
  listTables: (params: { branch_id: number }) =>
    apiClient
      .get<TableRead[]>("/api/v1/pos/tables", { params })
      .then((r) => r.data),

  createTable: (body: CreateTableRequest) =>
    apiClient
      .post<TableRead>("/api/v1/pos/tables", body)
      .then((r) => r.data),

  updateTableStatus: (tableId: number, body: UpdateTableStatusRequest) =>
    apiClient
      .patch<TableRead>(`/api/v1/pos/tables/${tableId}/status`, body)
      .then((r) => r.data),

  deleteTable: (tableId: number) =>
    apiClient.delete(`/api/v1/pos/tables/${tableId}`).then((r) => r.data),

  // ── Cash Sessions ────────────────────────────────────────────────────────
  getCurrentSession: (params: { branch_id: number }) =>
    apiClient
      .get<unknown>("/api/v1/pos/sessions/current", { params })
      .then((r) => r.data),

  openSession: (body: OpenSessionRequest) =>
    apiClient
      .post<unknown>("/api/v1/pos/sessions/open", body)
      .then((r) => r.data),

  closeSession: (sessionId: number, body: CloseSessionRequest) =>
    apiClient
      .post<unknown>(`/api/v1/pos/sessions/${sessionId}/close`, body)
      .then((r) => r.data),

  recordCashTransaction: (
    sessionId: number,
    body: CashTransactionRequest
  ) =>
    apiClient
      .post<unknown>(
        `/api/v1/pos/sessions/${sessionId}/transactions`,
        body
      )
      .then((r) => r.data),

  // ── Manager Override ─────────────────────────────────────────────────────
  requestOverride: (body: ManagerOverrideRequest) =>
    apiClient
      .post<{ grant_id: number }>("/api/v1/pos/override/request", body)
      .then((r) => r.data),

  // ── Reservations ─────────────────────────────────────────────────────────
  listReservations: (params: { branch_id: number; date?: string }) =>
    apiClient
      .get<unknown[]>("/api/v1/pos/reservations", { params })
      .then((r) => r.data),

  createReservation: (body: CreateReservationRequest) =>
    apiClient
      .post<unknown>("/api/v1/pos/reservations", body)
      .then((r) => r.data),

  updateReservationStatus: (
    reservationId: number,
    body: UpdateReservationStatusRequest
  ) =>
    apiClient
      .patch<unknown>(
        `/api/v1/pos/reservations/${reservationId}/status`,
        body
      )
      .then((r) => r.data),
};