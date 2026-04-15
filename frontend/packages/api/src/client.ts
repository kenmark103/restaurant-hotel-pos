/**
 * Typed Axios client for RestaurantOS API
 * Auto-wires auth headers, handles 401 → refresh → retry
 */
import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
} from "axios";

// ─── Types re-exported from schema ───────────────────────────────────────────
export type {
  components,
  paths,
  operations,
} from "./schema";

// Convenience aliases for the most-used schemas
export type LoginResponse =
  import("./schema").components["schemas"]["LoginResponse"];
export type UserSession =
  import("./schema").components["schemas"]["UserSession"];
export type Role = import("./schema").components["schemas"]["Role"];
export type OrderRead =
  import("./schema").components["schemas"]["OrderRead"];
export type OrderItemRead =
  import("./schema").components["schemas"]["OrderItemRead"];
export type TableRead =
  import("./schema").components["schemas"]["TableRead"];
export type TableStatus =
  import("./schema").components["schemas"]["TableStatus"];
export type CategoryRead =
  import("./schema").components["schemas"]["CategoryRead"];
export type MenuItemRead =
  import("./schema").components["schemas"]["MenuItemRead"];
export type KitchenStationResponse =
  import("./schema").components["schemas"]["KitchenStationResponse"];
export type KdsTicketStatus =
  import("./schema").components["schemas"]["KdsTicketStatus"];
export type PosOrderStatus =
  import("./schema").components["schemas"]["PosOrderStatus"];
export type PaymentMethod =
  import("./schema").components["schemas"]["PaymentMethod"];
export type StaffRead =
  import("./schema").components["schemas"]["StaffRead"];
export type ProductConfigurationResponse =
  import("./schema").components["schemas"]["ProductConfigurationResponse"];

// ─── Token store (in-memory only — never localStorage) ───────────────────────
let _accessToken: string | null = null;
let _refreshing: Promise<string | null> | null = null;

export function setAccessToken(token: string | null) {
  _accessToken = token;
}

export function getAccessToken(): string | null {
  return _accessToken;
}

// ─── Axios instance ───────────────────────────────────────────────────────────
export const apiClient: AxiosInstance = axios.create({
  baseURL: (import.meta as unknown as { env: Record<string, string> }).env
    ?.VITE_API_BASE_URL ?? "http://localhost:8000",
  timeout: 15_000,
  withCredentials: true, // needed for httpOnly refresh cookie
});

// ─── Request interceptor: inject Bearer token ────────────────────────────────
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (_accessToken) {
      config.headers.Authorization = `Bearer ${_accessToken}`;
    }
    return config;
  }
);

// ─── Response interceptor: 401 → refresh → retry once ───────────────────────
apiClient.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & {
      _retried?: boolean;
    };

    if (error.response?.status === 401 && !original?._retried) {
      original._retried = true;

      // Deduplicate concurrent refresh calls
      if (!_refreshing) {
        _refreshing = refreshAccessToken().finally(() => {
          _refreshing = null;
        });
      }

      const newToken = await _refreshing;
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(original);
      }

      // Refresh failed → clear token and let the app redirect to login
      setAccessToken(null);
      window.dispatchEvent(new CustomEvent("auth:logout"));
    }

    return Promise.reject(error);
  }
);

// ─── Refresh helper ───────────────────────────────────────────────────────────
async function refreshAccessToken(): Promise<string | null> {
  try {
    const res = await axios.post<LoginResponse>(
      `${apiClient.defaults.baseURL}/api/v1/auth/refresh`,
      {},
      { withCredentials: true }
    );
    const token = res.data.access_token;
    setAccessToken(token);
    return token;
  } catch {
    return null;
  }
}

// ─── Typed error helper ───────────────────────────────────────────────────────
export interface AppError {
  status: number;
  message: string;
  detail?: unknown;
}

export function parseApiError(error: unknown): AppError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status ?? 0;
    const data = error.response?.data as
      | { detail?: string | { msg: string }[] }
      | undefined;

    let message = "An unexpected error occurred.";
    if (typeof data?.detail === "string") {
      message = data.detail;
    } else if (Array.isArray(data?.detail)) {
      message = data.detail.map((d) => d.msg).join(", ");
    } else if (error.message) {
      message = error.message;
    }

    return { status, message, detail: data };
  }
  return { status: 0, message: String(error) };
}