import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createTable, CreateTablePayload, getTables, updateTableStatus } from '@/features/tables/api/tablesApi'
import { TableRecord } from '@/features/tables/types'

export const tableQueryKeys = {
  all: ['tables'] as const,
  list: (branchId?: number | null) => ['tables', branchId ?? 'all'] as const,
}

export function useTables(branchId?: number | null) {
  return useQuery({
    queryKey: tableQueryKeys.list(branchId),
    queryFn: () => getTables(branchId),
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  })
}

export function useUpdateTableStatus(branchId?: number | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ tableId, status }: { tableId: number; status: TableRecord['status'] }) => updateTableStatus(tableId, status),
    onSuccess: (updatedTable) => {
      queryClient.setQueryData<TableRecord[]>(tableQueryKeys.list(branchId), (currentTables = []) =>
        currentTables.map((table) => (table.id === updatedTable.id ? updatedTable : table)),
      )
    },
  })
}

export function useCreateTable(branchId?: number | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateTablePayload) => createTable(payload),
    onSuccess: (createdTable) => {
      queryClient.setQueryData<TableRecord[]>(tableQueryKeys.list(branchId), (current = []) => [createdTable, ...current])
    },
  })
}
