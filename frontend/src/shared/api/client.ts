import axios, { AxiosError, AxiosRequestConfig } from 'axios'

import { useAuthStore } from '@/store/authStore'

type RetryableRequestConfig = AxiosRequestConfig & {
  _retry?: boolean
  skipAuthRefresh?: boolean
}

export const apiClient = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
})

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let isRefreshing = false
let refreshQueue: Array<(token: string) => void> = []

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetryableRequestConfig | undefined

    if (!original || original.skipAuthRefresh) {
      return Promise.reject(error)
    }

    const requestUrl = original.url ?? ''
    const isRefreshRequest = requestUrl.includes('/auth/staff/refresh')

    if (error.response?.status === 401 && !original._retry && !isRefreshRequest) {
      original._retry = true

      if (isRefreshing) {
        return new Promise((resolve) => {
          refreshQueue.push((token) => {
            original.headers = { ...original.headers, Authorization: `Bearer ${token}` }
            resolve(apiClient(original))
          })
        })
      }

      isRefreshing = true
      try {
        const { data } = await axios.post('/api/v1/auth/staff/refresh', {}, { withCredentials: true })
        const newToken: string = data.access_token
        useAuthStore.getState().setAccessToken(newToken)

        refreshQueue.forEach((callback) => callback(newToken))
        refreshQueue = []

        original.headers = { ...original.headers, Authorization: `Bearer ${newToken}` }
        return apiClient(original)
      } catch (refreshError) {
        useAuthStore.getState().clearSession()
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)
