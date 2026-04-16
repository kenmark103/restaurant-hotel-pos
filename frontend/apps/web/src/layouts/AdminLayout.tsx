import { Outlet, Link, useRouter } from "@tanstack/react-router";
import { useState } from "react";
import { useSessionStore, can } from "@restaurantos/stores";
import {
  LayoutGrid, UtensilsCrossed, Package,
  BarChart2, Settings, Users, LogOut,
  Menu, X, ChefHat,
} from "lucide-react";
import { authApi } from "@restaurantos/api";
import { cn } from "@/lib/cn";

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
  capability?: Parameters<typeof can>[1];
}

const NAV: NavItem[] = [
  { label: "Floor",     path: "/pos",       icon: <LayoutGrid size={18} /> },
  { label: "Kitchen",   path: "/kitchen",   icon: <ChefHat size={18} /> },
  { label: "Menu",      path: "/menu",      icon: <UtensilsCrossed size={18} />, capability: "manage_settings" },
  { label: "Inventory", path: "/inventory", icon: <Package size={18} />,         capability: "manage_settings" },
  { label: "Reports",   path: "/reports",   icon: <BarChart2 size={18} />,       capability: "view_reports" },
  { label: "Staff",     path: "/staff",     icon: <Users size={18} />,           capability: "manage_staff" },
  { label: "Settings",  path: "/settings",  icon: <Settings size={18} />,        capability: "manage_settings" },
];

export function AdminLayout() {
  const { role, user, logout } = useSessionStore((s) => ({
    role: s.role,
    user: s.user,
    logout: s.logout,
  }));
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = async () => {
    try { await authApi.logout(); } catch { /* ignore */ }
    logout();
    router.navigate({ to: "/auth/pin" });
  };

  const visibleNav = NAV.filter((item) =>
    !item.capability || can(role, item.capability)
  );

  const currentPath = router.state.location.pathname;

  return (
    <div style={{
      display: "flex",
      height: "100dvh",
      background: "var(--color-brand)",
      overflow: "hidden",
    }}>

      {/* Sidebar */}
      <aside style={{
        width: sidebarOpen ? 220 : 64,
        flexShrink: 0,
        background: "var(--color-brand-2)",
        borderRight: "1px solid var(--color-border)",
        display: "flex",
        flexDirection: "column",
        transition: "width 0.2s ease",
        overflow: "hidden",
      }}>
        {/* Logo + toggle */}
        <div style={{
          height: 56,
          display: "flex",
          alignItems: "center",
          justifyContent: sidebarOpen ? "space-between" : "center",
          padding: sidebarOpen ? "0 16px" : "0 20px",
          borderBottom: "1px solid var(--color-border)",
          flexShrink: 0,
        }}>
          {sidebarOpen && (
            <span style={{
              fontFamily: "var(--font-display)",
              fontSize: 15,
              fontWeight: 700,
              color: "var(--color-text)",
              whiteSpace: "nowrap",
            }}>
              🧾 RestaurantOS
            </span>
          )}
          <button
            onClick={() => setSidebarOpen((o) => !o)}
            style={{
              background: "none", border: "none",
              color: "var(--color-muted)", cursor: "pointer",
              padding: 4, borderRadius: 6, lineHeight: 0,
            }}
          >
            {sidebarOpen ? <X size={16} /> : <Menu size={16} />}
          </button>
        </div>

        {/* Nav items */}
        <nav style={{ flex: 1, padding: "12px 8px", overflow: "hidden" }}>
          {visibleNav.map((item) => {
            const isActive = currentPath.startsWith(item.path);
            return (
              <Link key={item.path} to={item.path}>
                <div style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "10px 10px",
                  borderRadius: "var(--radius-sm)",
                  marginBottom: 2,
                  background: isActive
                    ? "rgba(59,130,246,0.15)"
                    : "transparent",
                  color: isActive
                    ? "var(--color-accent-2)"
                    : "var(--color-muted)",
                  cursor: "pointer",
                  transition: "all 0.15s",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  borderLeft: isActive
                    ? "2px solid var(--color-accent)"
                    : "2px solid transparent",
                }}>
                  <span style={{ flexShrink: 0 }}>{item.icon}</span>
                  {sidebarOpen && (
                    <span style={{
                      fontFamily: "var(--font-body)",
                      fontSize: 14,
                      fontWeight: isActive ? 500 : 400,
                    }}>
                      {item.label}
                    </span>
                  )}
                </div>
              </Link>
            );
          })}
        </nav>

        {/* User + logout */}
        <div style={{
          padding: "12px 8px",
          borderTop: "1px solid var(--color-border)",
        }}>
          {sidebarOpen && user && (
            <div style={{
              padding: "8px 10px",
              marginBottom: 4,
              overflow: "hidden",
            }}>
              <p style={{
                fontFamily: "var(--font-body)",
                fontSize: 13,
                fontWeight: 500,
                color: "var(--color-text)",
                margin: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}>
                {user.full_name}
              </p>
              <p style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                color: "var(--color-muted)",
                margin: "2px 0 0",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
              }}>
                {role}
              </p>
            </div>
          )}
          <button
            onClick={handleLogout}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: sidebarOpen ? "flex-start" : "center",
              gap: 10,
              width: "100%",
              padding: "10px 10px",
              borderRadius: "var(--radius-sm)",
              background: "none",
              border: "none",
              color: "var(--color-muted)",
              fontFamily: "var(--font-body)",
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            <LogOut size={16} />
            {sidebarOpen && "Log out"}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column" }}>
        <Outlet />
      </main>
    </div>
  );
}