import { create } from "zustand";
import type { UserSession, Role } from "@restaurantos/api";
import { setAccessToken } from "@restaurantos/api";

interface SessionState {
  // ── Data ────────────────────────────────────────────────────────────────
  user: UserSession | null;
  token: string | null;
  isHydrated: boolean;

  // ── Derived helpers ──────────────────────────────────────────────────────
  isAuthenticated: boolean;
  role: Role | null;
  branchId: number | null;

  // ── Actions ──────────────────────────────────────────────────────────────
  login: (token: string, user: UserSession) => void;
  logout: () => void;
  setToken: (token: string) => void;
  setHydrated: () => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  user: null,
  token: null,
  isHydrated: false,
  isAuthenticated: false,
  role: null,
  branchId: null,

  login: (token, user) => {
    setAccessToken(token);
    set({
      token,
      user,
      isAuthenticated: true,
      role: user.role ?? null,
      branchId: user.branch_id ?? null,
    });
  },

  logout: () => {
    setAccessToken(null);
    set({
      token: null,
      user: null,
      isAuthenticated: false,
      role: null,
      branchId: null,
    });
  },

  setToken: (token) => {
    setAccessToken(token);
    set({ token });
  },

  setHydrated: () => set({ isHydrated: true }),
}));

// ── Capability helpers ────────────────────────────────────────────────────────
const ROLE_WEIGHT: Record<Role, number> = {
  admin: 5,
  manager: 4,
  cashier: 3,
  server: 2,
  kitchen_manager: 3,
  kitchen: 1,
};

export function hasRole(
  userRole: Role | null,
  required: Role
): boolean {
  if (!userRole) return false;
  return (ROLE_WEIGHT[userRole] ?? 0) >= (ROLE_WEIGHT[required] ?? 99);
}

export type Capability =
  | "void_order"
  | "void_item"
  | "apply_discount"
  | "close_session"
  | "view_reports"
  | "manage_staff"
  | "manage_settings"
  | "view_staff_reports"
  | "bump_ticket"
  | "rush_ticket";

const CAPABILITY_MAP: Record<Capability, Role[]> = {
  void_order: ["manager", "admin"],
  void_item: ["manager", "admin", "cashier"],
  apply_discount: ["cashier", "server", "manager", "admin"],
  close_session: ["cashier", "manager", "admin"],
  view_reports: ["manager", "admin"],
  manage_staff: ["admin"],
  manage_settings: ["manager", "admin"],
  view_staff_reports: ["admin"],
  bump_ticket: ["kitchen", "kitchen_manager", "manager", "admin"],
  rush_ticket: ["kitchen_manager", "manager", "admin"],
};

export function can(role: Role | null, capability: Capability): boolean {
  if (!role) return false;
  const allowed = CAPABILITY_MAP[capability];
  if (role === "admin") return true;
  return allowed.includes(role);
}