import { apiClient } from '@/shared/api/client'

import { AccessTokenResponse, CurrentUserResponse, GoogleStartResponse, StaffLoginPayload } from '../types'

export const authApi = {
  async loginStaff(payload: StaffLoginPayload) {
    const response = await apiClient.post<AccessTokenResponse>('/auth/staff/login', payload)
    return response.data
  },
  async getCurrentUser() {
    const response = await apiClient.get<CurrentUserResponse>('/me')
    return response.data
  },
  async getGoogleStart() {
    const response = await apiClient.post<GoogleStartResponse>('/auth/customers/google/start')
    return response.data
  },
  async logout() {
    await apiClient.post('/auth/logout')
  },
}

export const { getCurrentUser, getGoogleStart, loginStaff, logout } = authApi
