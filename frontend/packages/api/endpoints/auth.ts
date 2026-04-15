import { apiClient } from "../src/client";
import type { components } from "@restaurantos/schemas";

type LoginResponse = components["schemas"]["LoginResponse"];
type PinLoginRequest = components["schemas"]["PinLoginRequest"];
type StaffLoginRequest = components["schemas"]["StaffLoginRequest"];
type UserSession = components["schemas"]["UserSession"];

export const authApi = {
  /**
   * Primary POS login — 5-digit PIN + branch
   * POST /api/v1/auth/pin-login
   */
  pinLogin: (body: PinLoginRequest) =>
    apiClient
      .post<LoginResponse>("/api/v1/auth/pin-login", body)
      .then((r) => r.data),

  /**
   * Email + password fallback (first setup, admin)
   * POST /api/v1/auth/staff/login
   */
  staffLogin: (body: StaffLoginRequest) =>
    apiClient
      .post<LoginResponse>("/api/v1/auth/staff/login", body)
      .then((r) => r.data),

  /**
   * Get current session user from token
   * GET /api/v1/auth/me
   */
  me: () =>
    apiClient.get<UserSession>("/api/v1/auth/me").then((r) => r.data),

  /**
   * Logout — clears httpOnly refresh cookie on server
   * POST /api/v1/auth/logout
   */
  logout: () =>
    apiClient.post<void>("/api/v1/auth/logout").then((r) => r.data),

  /**
   * Refresh access token using httpOnly cookie
   * POST /api/v1/auth/refresh
   */
  refresh: () =>
    apiClient
      .post<LoginResponse>("/api/v1/auth/refresh")
      .then((r) => r.data),
};