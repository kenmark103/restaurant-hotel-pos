import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  addOrderItem,
  closeOrder,
  createOrder,
  getOrder,
  getOrders,
  holdOrder,
  sendOrder,
  updateOrderItem,
  voidOrder,
  voidOrderItem,
} from '@/features/orders/api/ordersApi'
import type {
  AddOrderItemPayload,
  CloseOrderPayload,
  CreateOrderPayload,
  UpdateOrderItemPayload,
  VoidOrderItemPayload,
} from '@/features/orders/types'

export const orderQueryKeys = {
  list: (branchId?: number | null, activeOnly: boolean = true) => ['orders', branchId ?? 'all', activeOnly] as const,
  detail: (orderId: number | null) => ['orders', 'detail', orderId] as const,
}

function invalidateRuntimeQueries(queryClient: ReturnType<typeof useQueryClient>, branchId?: number | null) {
  void queryClient.invalidateQueries({ queryKey: orderQueryKeys.list(branchId, true) })
  void queryClient.invalidateQueries({ queryKey: ['tables'] })
}

export function useOrders(branchId?: number | null, activeOnly: boolean = true) {
  return useQuery({
    queryKey: orderQueryKeys.list(branchId, activeOnly),
    queryFn: () => getOrders({ branchId, activeOnly }),
    staleTime: 15 * 1000,
    refetchInterval: activeOnly ? 30 * 1000 : 60 * 1000,
    refetchOnWindowFocus: false,
  })
}

export function useActiveOrders(branchId?: number | null) {
  return useOrders(branchId, true)
}

export function useAllOrders(branchId?: number | null) {
  return useOrders(branchId, false)
}

export function useOrderDetail(orderId: number | null) {
  return useQuery({
    queryKey: orderQueryKeys.detail(orderId),
    queryFn: () => getOrder(orderId!),
    enabled: orderId != null,
    staleTime: 3 * 1000,
    refetchOnWindowFocus: false,
  })
}

export function useCreateOrder(branchId?: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreateOrderPayload) => createOrder(payload),
    onSuccess: (order) => {
      invalidateRuntimeQueries(queryClient, branchId)
      queryClient.setQueryData(orderQueryKeys.detail(order.id), order)
    },
  })
}

export function useAddOrderItem(branchId?: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, payload }: { orderId: number; payload: AddOrderItemPayload }) =>
      addOrderItem(orderId, payload),
    onSuccess: (order) => {
      invalidateRuntimeQueries(queryClient, branchId)
      queryClient.setQueryData(orderQueryKeys.detail(order.id), order)
    },
  })
}

export function useUpdateOrderItem(branchId?: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, itemId, payload }: { orderId: number; itemId: number; payload: UpdateOrderItemPayload }) =>
      updateOrderItem(orderId, itemId, payload),
    onSuccess: (order) => {
      invalidateRuntimeQueries(queryClient, branchId)
      queryClient.setQueryData(orderQueryKeys.detail(order.id), order)
    },
  })
}

export function useVoidOrderItem(branchId?: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, itemId, payload }: { orderId: number; itemId: number; payload?: VoidOrderItemPayload }) =>
      voidOrderItem(orderId, itemId, payload),
    onSuccess: (order) => {
      invalidateRuntimeQueries(queryClient, branchId)
      queryClient.setQueryData(orderQueryKeys.detail(order.id), order)
    },
  })
}

export function useSendOrder(branchId?: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (orderId: number) => sendOrder(orderId),
    onSuccess: (order) => {
      invalidateRuntimeQueries(queryClient, branchId)
      queryClient.setQueryData(orderQueryKeys.detail(order.id), order)
    },
  })
}

export function useHoldOrder(branchId?: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (orderId: number) => holdOrder(orderId),
    onSuccess: (order) => {
      invalidateRuntimeQueries(queryClient, branchId)
      queryClient.setQueryData(orderQueryKeys.detail(order.id), order)
    },
  })
}

export function useVoidOrder(branchId?: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, payload }: { orderId: number; payload?: VoidOrderItemPayload }) =>
      voidOrder(orderId, payload),
    onSuccess: (order) => {
      invalidateRuntimeQueries(queryClient, branchId)
      queryClient.setQueryData(orderQueryKeys.detail(order.id), order)
    },
  })
}

export function useCloseOrder(branchId?: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, payload }: { orderId: number; payload: CloseOrderPayload }) =>
      closeOrder(orderId, payload),
    onSuccess: (order) => {
      invalidateRuntimeQueries(queryClient, branchId)
      queryClient.setQueryData(orderQueryKeys.detail(order.id), order)
    },
  })
}
