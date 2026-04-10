import { apiClient } from '@/shared/api/client'

export interface BranchRecord {
  id: number
  name: string
  code: string
  address: string | null
  phone: string | null
  timezone: string
  is_active: boolean
}

export async function getBranches() {
  const response = await apiClient.get<BranchRecord[]>('/branches/')
  return response.data
}

export interface CreateBranchPayload {
  name: string
  code: string
  address?: string | null
  phone?: string | null
  timezone?: string
}

export async function createBranch(payload: CreateBranchPayload) {
  const response = await apiClient.post<BranchRecord>('/branches/', payload)
  return response.data
}
