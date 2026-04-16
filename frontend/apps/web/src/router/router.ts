import {
  createRouter,
  createRoute,
  createRootRoute,
  redirect,
} from "@tanstack/react-router";
import { lazy } from "react";
import { useSessionStore } from "@restaurantos/stores";
import { RootLayout } from "@/layouts/RootLayout";

// ─── Lazy-loaded screens ─────────────────────────────────────────────────────
const PinPadScreen      = lazy(() => import("@/features/auth/PinPadScreen"));
const EmailLoginScreen  = lazy(() => import("@/features/auth/EmailLoginScreen"));
const FloorViewScreen   = lazy(() => import("@/features/pos/FloorViewScreen"));
const OrderScreen       = lazy(() => import("@/features/pos/OrderScreen"));

// Week 3+ screens — stub until implemented
const KdsScreen       = lazy(() =>
  import("@/features/shared/stubs").then((m) => ({ default: m.KdsScreen }))
);
const MenuScreen      = lazy(() =>
  import("@/features/shared/stubs").then((m) => ({ default: m.MenuScreen }))
);
const InventoryScreen = lazy(() =>
  import("@/features/shared/stubs").then((m) => ({ default: m.InventoryScreen }))
);
const ReportsScreen   = lazy(() =>
  import("@/features/shared/stubs").then((m) => ({ default: m.ReportsScreen }))
);
const SettingsScreen  = lazy(() =>
  import("@/features/shared/stubs").then((m) => ({ default: m.SettingsScreen }))
);
const StaffScreen     = lazy(() =>
  import("@/features/shared/stubs").then((m) => ({ default: m.StaffScreen }))
);
const NotFoundScreen  = lazy(() =>
  import("@/features/shared/stubs").then((m) => ({ default: m.NotFoundScreen }))
);

// ─── Auth guard helper ───────────────────────────────────────────────────────
function requireAuth() {
  const { isAuthenticated } = useSessionStore.getState();
  if (!isAuthenticated) throw redirect({ to: "/auth/pin" });
}

function requireRole(...roles: string[]) {
  return () => {
    const { isAuthenticated, role } = useSessionStore.getState();
    if (!isAuthenticated) throw redirect({ to: "/auth/pin" });
    if (!role || !roles.includes(role)) throw redirect({ to: "/pos" });
  };
}

// ─── Root route ───────────────────────────────────────────────────────────────
const rootRoute = createRootRoute({ component: RootLayout });

// ─── Auth routes ──────────────────────────────────────────────────────────────
const authPinRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/auth/pin",
  component: PinPadScreen,
});

const authLoginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/auth/login",
  component: EmailLoginScreen,
});

// ─── POS routes ───────────────────────────────────────────────────────────────
const posRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/pos",
  beforeLoad: requireAuth,
  component: FloorViewScreen,
});

const orderRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/pos/order/$orderId",
  beforeLoad: requireAuth,
  component: OrderScreen,
});

// ─── Kitchen ──────────────────────────────────────────────────────────────────
const kdsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/kitchen",
  beforeLoad: requireRole(
    "kitchen",
    "kitchen_manager",
    "manager",
    "admin"
  ),
  component: KdsScreen,
});

// ─── Admin screens ────────────────────────────────────────────────────────────
const menuRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/menu",
  beforeLoad: requireRole("manager", "admin"),
  component: MenuScreen,
});

const inventoryRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/inventory",
  beforeLoad: requireRole("manager", "admin"),
  component: InventoryScreen,
});

const reportsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/reports",
  beforeLoad: requireRole("manager", "admin"),
  component: ReportsScreen,
});

const settingsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/settings",
  beforeLoad: requireRole("manager", "admin"),
  component: SettingsScreen,
});

const staffRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/staff",
  beforeLoad: requireRole("admin"),
  component: StaffScreen,
});

// ─── Redirect / → /auth/pin ───────────────────────────────────────────────────
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: () => {
    const { isAuthenticated, role } = useSessionStore.getState();
    if (isAuthenticated) {
      if (
        role === "kitchen" ||
        role === "kitchen_manager"
      ) {
        throw redirect({ to: "/kitchen" });
      }
      throw redirect({ to: "/pos" });
    }
    throw redirect({ to: "/auth/pin" });
  },
  component: () => null,
});

const notFoundRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "*",
  component: NotFoundScreen,
});

// ─── Router ───────────────────────────────────────────────────────────────────
const routeTree = rootRoute.addChildren([
  indexRoute,
  authPinRoute,
  authLoginRoute,
  posRoute,
  orderRoute,
  kdsRoute,
  menuRoute,
  inventoryRoute,
  reportsRoute,
  settingsRoute,
  staffRoute,
  notFoundRoute,
]);

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}