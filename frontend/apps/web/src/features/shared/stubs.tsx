// ─────────────────────────────────────────────────────────────────────────────
// Stub screens — these will be fully implemented in Weeks 2-5.
// Each file is a separate named export for lazy loading.
// ─────────────────────────────────────────────────────────────────────────────

import { useNavigate } from "@tanstack/react-router";
import { useSessionStore } from "@restaurantos/stores";
import { LogOut } from "lucide-react";

function ComingSoon({ title }: { title: string }) {
  const navigate = useNavigate();
  const logout = useSessionStore((s) => s.logout);

  const handleLogout = async () => {
    logout();
    navigate({ to: "/auth/pin" });
  };

  return (
    <div style={{
      minHeight: "100dvh",
      background: "var(--color-brand)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: 12,
    }}>
      <span style={{
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        color: "var(--color-accent)",
        letterSpacing: "0.15em",
        textTransform: "uppercase",
      }}>
        Coming Week 2
      </span>
      <h1 style={{
        fontFamily: "var(--font-display)",
        fontSize: 32,
        fontWeight: 700,
        color: "var(--color-text)",
        margin: 0,
        letterSpacing: "-0.5px",
      }}>
        {title}
      </h1>
      <p style={{
        fontFamily: "var(--font-mono)",
        fontSize: 12,
        color: "var(--color-muted)",
        margin: "4px 0 24px",
      }}>
        Backend is locked. Frontend coming next.
      </p>
      <button
        onClick={handleLogout}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          padding: "10px 20px",
          background: "var(--color-brand-2)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-md)",
          color: "var(--color-muted)",
          fontFamily: "var(--font-mono)",
          fontSize: 12,
          cursor: "pointer",
          letterSpacing: "0.05em",
        }}
      >
        <LogOut size={13} /> Logout
      </button>
    </div>
  );
}

// Individual stub exports (one file per module for lazy() to work)
const FloorViewScreen = () => <ComingSoon title="Floor View" />;
const OrderScreen     = () => <ComingSoon title="Order Screen" />;
const KdsScreen       = () => <ComingSoon title="Kitchen Display" />;
const MenuScreen      = () => <ComingSoon title="Menu Management" />;
const InventoryScreen = () => <ComingSoon title="Inventory" />;
const ReportsScreen   = () => <ComingSoon title="Reports" />;
const SettingsScreen  = () => <ComingSoon title="Settings" />;
const StaffScreen     = () => <ComingSoon title="Staff Management" />;
const NotFoundScreen  = () => <ComingSoon title="404 — Not Found" />;

export {
  FloorViewScreen,
  OrderScreen,
  KdsScreen,
  MenuScreen,
  InventoryScreen,
  ReportsScreen,
  SettingsScreen,
  StaffScreen,
  NotFoundScreen,
};