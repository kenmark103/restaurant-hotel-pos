/**
 * Central hooks file — all TanStack Query hooks.
 * Rule: if the server owns it, it lives here.
 */
import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import {
  posApi,
  productsApi,
  kitchenApi,
  inventoryApi,
  reportsApi,
  settingsApi,
  staffApi,
  authApi,
  type OrderRead,
  type CategoryRead,
} from "@restaurantos/api";
import { useSessionStore } from "@restaurantos/stores";
import { getCachedMenu, setCachedMenu, getCachedTables, setCachedTables } from "@/lib/db";

// ─── Auth ─────────────────────────────────────────────────────────────────────
export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: authApi.me,
    staleTime: 1000 * 60 * 5,
  });
}

// ─── Tables ───────────────────────────────────────────────────────────────────
export function useTables() {
  const branchId = useSessionStore((s) => s.branchId);
  return useQuery({
    queryKey: ["tables", branchId],
    queryFn: async () => {
      if (!branchId) return [];
      try {
        const data = await posApi.listTables({ branch_id: branchId });
        await setCachedTables(branchId, data);
        return data;
      } catch {
        // Offline fallback
        const cached = await getCachedTables(branchId!);
        return (cached as typeof data) ?? [];
      }
    },
    enabled: !!branchId,
    staleTime: 1000 * 30,
  });
}

// ─── Orders ───────────────────────────────────────────────────────────────────
export function useOrders(status?: string) {
  const branchId = useSessionStore((s) => s.branchId);
  return useQuery({
    queryKey: ["orders", branchId, status],
    queryFn: () =>
      posApi.listOrders({
        branch_id: branchId!,
        status,
        limit: 100,
      }),
    enabled: !!branchId,
    staleTime: 1000 * 10,
  });
}

export function useOrder(orderId: number | null) {
  return useQuery({
    queryKey: ["order", orderId],
    queryFn: () => posApi.getOrder(orderId!),
    enabled: !!orderId,
    staleTime: 1000 * 5,
  });
}

// ─── Menu ─────────────────────────────────────────────────────────────────────
export function useMenu() {
  const branchId = useSessionStore((s) => s.branchId);
  return useQuery({
    queryKey: ["menu", branchId],
    queryFn: async () => {
      try {
        const data = await productsApi.getPublicMenu({
          branch_id: branchId ?? undefined,
        });
        await setCachedMenu(branchId ?? 0, data);
        return data;
      } catch {
        const cached = await getCachedMenu(branchId ?? 0);
        return (cached as CategoryRead[]) ?? [];
      }
    },
    enabled: true,
    staleTime: 1000 * 60 * 5,
  });
}

export function useCategoryTree() {
  const branchId = useSessionStore((s) => s.branchId);
  return useQuery({
    queryKey: ["category-tree", branchId],
    queryFn: () =>
      productsApi.getCategoryTree({ branch_id: branchId ?? undefined }),
    staleTime: 1000 * 60 * 5,
  });
}

// ─── KDS Tickets ──────────────────────────────────────────────────────────────
export function useKdsTickets(stationId?: string) {
  const branchId = useSessionStore((s) => s.branchId);
  return useQuery({
    queryKey: ["kds-tickets", branchId, stationId],
    queryFn: () =>
      kitchenApi.listTickets({
        branch_id: branchId!,
        station_id: stationId,
        status: "pending,preparing",
      }),
    enabled: !!branchId,
    staleTime: 1000 * 5,
    refetchInterval: 30_000, // fallback poll every 30s
  });
}

// ─── Cash Session ─────────────────────────────────────────────────────────────
export function useCurrentSession() {
  const branchId = useSessionStore((s) => s.branchId);
  return useQuery({
    queryKey: ["session-current", branchId],
    queryFn: () =>
      posApi.getCurrentSession({ branch_id: branchId! }),
    enabled: !!branchId,
    staleTime: 1000 * 60,
  });
}

// ─── Product Config (units, stations, taxes) ──────────────────────────────────
export function useProductConfig() {
  return useQuery({
    queryKey: ["product-config"],
    queryFn: settingsApi.getProductConfiguration,
    staleTime: 1000 * 60 * 30,
  });
}

// ─── Staff ────────────────────────────────────────────────────────────────────
export function useStaff(branchId?: number) {
  return useQuery({
    queryKey: ["staff", branchId],
    queryFn: () => staffApi.listStaff({ branch_id: branchId }),
    staleTime: 1000 * 60 * 10,
  });
}

// ─── Reports ──────────────────────────────────────────────────────────────────
export function useReportDaily(date?: string) {
  const branchId = useSessionStore((s) => s.branchId);
  return useQuery({
    queryKey: ["report-daily", branchId, date],
    queryFn: () =>
      reportsApi.getDaily({ branch_id: branchId!, date }),
    enabled: !!branchId,
    staleTime: 0,
  });
}

export function useTopItems(params?: {
  date_from?: string;
  date_to?: string;
  limit?: number;
}) {
  const branchId = useSessionStore((s) => s.branchId);
  return useQuery({
    queryKey: ["report-items", branchId, params],
    queryFn: () =>
      reportsApi.getTopItems({ branch_id: branchId!, ...params }),
    enabled: !!branchId,
    staleTime: 0,
  });
}

export function useStockLevels() {
  const branchId = useSessionStore((s) => s.branchId);
  return useQuery({
    queryKey: ["stock-levels", branchId],
    queryFn: () =>
      inventoryApi.listStockLevels({ branch_id: branchId! }),
    enabled: !!branchId,
    staleTime: 1000 * 60 * 2,
    refetchInterval: 1000 * 60 * 2,
  });
}

// ─── Venue Settings ────────────────────────────────────────────────────────────
export function useVenueSettings() {
  return useQuery({
    queryKey: ["venue-settings"],
    queryFn: settingsApi.getVenue,
    staleTime: 1000 * 60 * 30,
  });
}

// ─── Mutations ────────────────────────────────────────────────────────────────
export function useCreateOrder() {
  const qc = useQueryClient();
  const branchId = useSessionStore((s) => s.branchId);
  return useMutation({
    mutationFn: posApi.createOrder,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["orders", branchId] });
      qc.invalidateQueries({ queryKey: ["tables", branchId] });
    },
  });
}

export function useAddItem(orderId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof posApi.addItem>[1]) =>
      posApi.addItem(orderId, body),
    onSuccess: (updatedOrder: OrderRead) => {
      qc.setQueryData(["order", orderId], updatedOrder);
    },
  });
}

export function useVoidItem(orderId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      itemId,
      reason,
    }: {
      itemId: number;
      reason: string;
    }) => posApi.voidItem(orderId, itemId, { reason }),
    onSuccess: (updatedOrder: OrderRead) => {
      qc.setQueryData(["order", orderId], updatedOrder);
    },
  });
}

export function useSendToKitchen(orderId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (stationFilter?: string) =>
      posApi.sendToKitchen(orderId, {
        station_filter: stationFilter,
      }),
    onSuccess: (updatedOrder: OrderRead) => {
      qc.setQueryData(["order", orderId], updatedOrder);
      qc.invalidateQueries({ queryKey: ["kds-tickets"] });
    },
  });
}

export function useCloseOrder(orderId: number) {
  const qc = useQueryClient();
  const branchId = useSessionStore((s) => s.branchId);
  return useMutation({
    mutationFn: (body: Parameters<typeof posApi.closeOrder>[1]) =>
      posApi.closeOrder(orderId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["orders", branchId] });
      qc.invalidateQueries({ queryKey: ["tables", branchId] });
      qc.removeQueries({ queryKey: ["order", orderId] });
    },
  });
}

export function useUpdateTicketStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      ticketId,
      status,
    }: {
      ticketId: number;
      status: string;
    }) => kitchenApi.updateTicketStatus(ticketId, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kds-tickets"] });
    },
  });
}

export function useRequestOverride() {
  return useMutation({
    mutationFn: posApi.requestOverride,
  });
}