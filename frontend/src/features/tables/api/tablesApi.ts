import { apiClient } from '@/shared/api/client'

import { TableRecord } from '../types'

export async function getTables(branchId?: number | null) {
  const suffix = branchId ? `?branch_id=${branchId}` : ''
  const response = await apiClient.get<TableRecord[]>(`/tables/${suffix}`)
  return response.data
}

export async function updateTableStatus(tableId: number, status: TableRecord['status']) {
  const response = await apiClient.patch<TableRecord>(`/tables/${tableId}/status`, { status })
  return response.data
}

export interface CreateTablePayload {
  branch_id: number
  table_number: string
  capacity: number
}

export async function createTable(payload: CreateTablePayload) {
  const response = await apiClient.post<TableRecord>('/tables/', payload)
  return response.data
}
