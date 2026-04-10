import { apiClient } from '@/shared/api/client'

import { StaffMember } from '../types'


export interface ActivateStaffPayload {
  token: string
  password: string
}

export async function activateStaffAccount(payload: ActivateStaffPayload): Promise<void> {
  await apiClient.post('/staff/activate', payload)
}

export async function getStaffMembers() {
  const response = await apiClient.get<StaffMember[]>('/staff/')
  return response.data
}

export interface InviteStaffPayload {
  email: string
  full_name: string
  role: 'admin' | 'manager' | 'cashier' | 'server' | 'kitchen'
  branch_id: number | null
}

export interface InviteStaffResponse {
  detail: string
  activation_token: string | null
}

export async function inviteStaffMember(payload: InviteStaffPayload) {
  const response = await apiClient.post<InviteStaffResponse>('/staff/invite', payload)
  return response.data
}

export async function disableStaffMember(staffId: number) {
  const response = await apiClient.patch<{ detail: string }>(`/staff/${staffId}/disable`)
  return response.data
}
