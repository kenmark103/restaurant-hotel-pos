import { Outlet } from "@tanstack/react-router";
import { Suspense, useEffect } from "react";
import { useSessionStore } from "@restaurantos/stores";
import { connectSocket, disconnectSocket } from "@/lib/socket";

export function RootLayout() {
  const { isAuthenticated, token, branchId, logout } = useSessionStore(
    (s) => ({
      isAuthenticated: s.isAuthenticated,
      token: s.token,
      branchId: s.branchId,
      logout: s.logout,
    })
  );

  // Connect socket when authenticated
  useEffect(() => {
    if (isAuthenticated && token && branchId) {
      connectSocket(token, branchId);
    }
    return () => {
      if (!isAuthenticated) disconnectSocket();
    };
  }, [isAuthenticated, token, branchId]);

  // Listen for auth:logout events (fired by Axios 401 handler)
  useEffect(() => {
    const handler = () => logout();
    window.addEventListener("auth:logout", handler);
    return () => window.removeEventListener("auth:logout", handler);
  }, [logout]);

  return (
    <Suspense fallback={<AppLoader />}>
      <Outlet />
    </Suspense>
  );
}

function AppLoader() {
  return (
    <div className="flex h-full items-center justify-center"
      style={{ background: "var(--color-brand)" }}>
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 rounded-full border-2 border-t-transparent animate-spin"
          style={{ borderColor: "var(--color-accent)" }} />
        <span style={{ color: "var(--color-muted)", fontFamily: "var(--font-mono)", fontSize: 13 }}>
          loading...
        </span>
      </div>
    </div>
  );
}