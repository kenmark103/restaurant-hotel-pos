import { apiClient } from '@/shared/api/client'

import type {
  AddOrderItemPayload,
  CloseOrderPayload,
  CreateOrderPayload,
  PosOrder,
  UpdateOrderItemPayload,
  VoidOrderItemPayload,
} from '../types'

export async function getOrders(params: { branchId?: number | null; activeOnly?: boolean } = {}) {
  const query = new URLSearchParams()
  if (params.branchId != null) {
    query.set('branch_id', String(params.branchId))
  }
  if (params.activeOnly != null) {
    query.set('active_only', String(params.activeOnly))
  }
  const suffix = query.toString() ? `?${query.toString()}` : ''
  const response = await apiClient.get<PosOrder[]>(`/orders${suffix}`)
  return response.data
}

export async function getOrder(orderId: number) {
  const response = await apiClient.get<PosOrder>(`/orders/${orderId}`)
  return response.data
}

export async function createOrder(payload: CreateOrderPayload) {
  const response = await apiClient.post<PosOrder>('/orders/', payload)
  return response.data
}

export async function addOrderItem(orderId: number, payload: AddOrderItemPayload) {
  const response = await apiClient.post<PosOrder>(`/orders/${orderId}/items`, payload)
  return response.data
}

export async function updateOrderItem(orderId: number, itemId: number, payload: UpdateOrderItemPayload) {
  const response = await apiClient.patch<PosOrder>(`/orders/${orderId}/items/${itemId}`, payload)
  return response.data
}

export async function voidOrderItem(orderId: number, itemId: number, payload: VoidOrderItemPayload = {}) {
  const response = await apiClient.post<PosOrder>(`/orders/${orderId}/items/${itemId}/void`, payload)
  return response.data
}

export async function sendOrder(orderId: number) {
  const response = await apiClient.post<PosOrder>(`/orders/${orderId}/send`)
  return response.data
}

export async function holdOrder(orderId: number) {
  const response = await apiClient.post<PosOrder>(`/orders/${orderId}/hold`)
  return response.data
}

export async function voidOrder(orderId: number, payload: VoidOrderItemPayload = {}) {
  const response = await apiClient.post<PosOrder>(`/orders/${orderId}/void`, payload)
  return response.data
}

export async function closeOrder(orderId: number, payload: CloseOrderPayload) {
  const response = await apiClient.post<PosOrder>(`/orders/${orderId}/close`, payload)
  return response.data
}
