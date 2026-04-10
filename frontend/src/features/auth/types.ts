import { AuthUser } from '@/store/authStore'

export interface AccessTokenResponse {
  access_token: string
  token_type: string
}

export interface StaffLoginPayload {
  email: string
  password: string
}

export interface GoogleStartResponse {
  enabled: boolean
  authorization_url: string | null
  message: string
}

export type CurrentUserResponse = AuthUser
