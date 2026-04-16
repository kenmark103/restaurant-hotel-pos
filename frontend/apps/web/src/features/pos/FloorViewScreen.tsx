import { useState, useEffect } from "react";
import { useNavigate, Link } from "@tanstack/react-router";
import {
  useTables, useOrders, useCreateOrder,
  useCurrentSession, useProductConfig
} from "@/hooks/useApi";
import { useSessionStore, useCashStore, can } from "@restaurantos/stores";
import { posApi, type TableRead } from "@restaurantos/api";
import { cn, fmt } from "@/lib/cn";
import {
  Plus, Clock, Receipt, ChefHat, BarChart2,
  Settings, Users, Wifi, WifiOff, AlertTriangle,
  Package
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

// ─── Types ────────────────────────────────────────────────────────────────────
type TableStatus = "available" | "occupied" | "reserved" | "cleaning";

interface EnrichedTable extends TableRead {
  status: TableStatus;
  activeOrderId?: number;
  orderOpenedAt?: string;
  totalAmount?: string;
  guestCount?: number;
}

const ORDER_ALERT_MINUTES = 90;

// ─── Main Component ───────────────────────────────────────────────────────────
export default function FloorViewScreen() {
  const navigate = useNavigate();
  const { role, branchId, user } = useSessionStore((s) => ({
    role: s.role,
    branchId: s.branchId,
    user: s.user,
  }));
  const { sessionId } = useCashStore();

  const [orderTypeModal, setOrderTypeModal] = useState(false);
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  // Data
  const { data: tables = [], isLoading: tablesLoading } = useTables();
  const { data: orders = [] } = useOrders("open,sent");
  const { data: session } = useCurrentSession();
  const createOrder = useCreateOrder();

  // Online/offline
  useEffect(() => {
    const on  = () => setIsOnline(true);
    const off = () => setIsOnline(false);
    window.addEventListener("online",  on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online",  on);
      window.removeEventListener("offline", off);
    };
  }, []);

  // Enrich tables with their active order
  const enrichedTables: EnrichedTable[] = tables.map((table) => {
    const activeOrder = (orders as any[]).find(
      (o: any) => o.table?.id === table.id && (o.status === "open" || o.status === "sent")
    );
    if (activeOrder) {
      return {
        ...table,
        status: "occupied",
        activeOrderId: activeOrder.id,
        orderOpenedAt: activeOrder.created_at,
        totalAmount: activeOrder.total_amount,
      };
    }
    return { ...table, status: "available" };
  });

  const openOrders = (orders as any[]).filter(
    (o: any) => o.status === "open" || o.status === "sent"
  );
  const counterOrders = openOrders.filter((o: any) => !o.table);

  const handleTableClick = (table: EnrichedTable) => {
    if (table.status === "occupied" && table.activeOrderId) {
      navigate({ to: `/pos/order/${table.activeOrderId}` });
    } else if (table.status === "available") {
      // Create dine-in order immediately
      createOrder.mutate(
        {
          order_type: "dine_in",
          branch_id: branchId!,
          table_id: table.id,
        },
        {
          onSuccess: (order) => {
            navigate({ to: `/pos/order/${order.id}` });
          },
        }
      );
    }
  };

  const handleNewOrder = (type: "counter" | "takeaway") => {
    setOrderTypeModal(false);
    createOrder.mutate(
      {
        order_type: type,
        branch_id: branchId!,
      },
      {
        onSuccess: (order) => {
          navigate({ to: `/pos/order/${order.id}` });
        },
      }
    );
  };

  const sessionWarning = !session;

  return (
    <div style={{
      height: "100dvh",
      display: "flex",
      flexDirection: "column",
      background: "var(--color-brand)",
      overflow: "hidden",
    }}>

      {/* ── Top bar ───────────────────────────────────────────────────────── */}
      <header style={{
        height: 52,
        background: "var(--color-brand-2)",
        borderBottom: "1px solid var(--color-border)",
        display: "flex",
        alignItems: "center",
        gap: 12,
        paddingInline: 16,
        flexShrink: 0,
      }}>
        {/* Logo */}
        <span style={{
          fontFamily: "var(--font-display)",
          fontSize: 16, fontWeight: 700,
          color: "var(--color-text)",
          marginRight: 4,
        }}>
          🧾
        </span>

        {/* Session warning */}
        {sessionWarning && (
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "4px 10px",
            background: "rgba(245,158,11,0.12)",
            border: "1px solid rgba(245,158,11,0.3)",
            borderRadius: 6,
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            color: "var(--color-warning)",
          }}>
            <AlertTriangle size={12} />
            No cash session open
          </div>
        )}

        <div style={{ flex: 1 }} />

        {/* Nav links for managers */}
        {can(role, "view_reports") && (
          <>
            <NavBtn icon={<ChefHat size={15} />} label="KDS" to="/kitchen" />
            <NavBtn icon={<BarChart2 size={15} />} label="Reports" to="/reports" />
          </>
        )}
        {can(role, "manage_settings") && (
          <>
            <NavBtn icon={<Package size={15} />} label="Inventory" to="/inventory" />
            <NavBtn icon={<Settings size={15} />} label="Settings" to="/settings" />
          </>
        )}
        {can(role, "manage_staff") && (
          <NavBtn icon={<Users size={15} />} label="Staff" to="/staff" />
        )}

        {/* Online status */}
        <div style={{
          display: "flex", alignItems: "center", gap: 5,
          fontFamily: "var(--font-mono)", fontSize: 11,
          color: isOnline ? "var(--color-success)" : "var(--color-danger)",
          marginLeft: 8,
        }}>
          {isOnline ? <Wifi size={13} /> : <WifiOff size={13} />}
        </div>

        {/* Staff name */}
        <div style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          color: "var(--color-muted)",
          paddingLeft: 12,
          borderLeft: "1px solid var(--color-border)",
        }}>
          {user?.full_name?.split(" ")[0]}
        </div>
      </header>

      {/* ── Body ──────────────────────────────────────────────────────────── */}
      <div style={{
        flex: 1,
        display: "grid",
        gridTemplateColumns: "1fr 280px",
        overflow: "hidden",
      }}>

        {/* ── Table grid ──────────────────────────────────────────────────── */}
        <div style={{
          overflow: "auto",
          padding: 24,
          display: "flex",
          flexDirection: "column",
          gap: 20,
        }}>

          {/* Actions row */}
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <h2 style={{
              fontFamily: "var(--font-display)",
              fontSize: 20, fontWeight: 700,
              color: "var(--color-text)",
              margin: 0,
            }}>
              Floor View
            </h2>
            <div style={{ flex: 1 }} />
            <button
              onClick={() => setOrderTypeModal(true)}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "10px 18px",
                background: "var(--color-accent)",
                border: "none",
                borderRadius: "var(--radius-md)",
                color: "#fff",
                fontFamily: "var(--font-display)",
                fontSize: 14, fontWeight: 700,
                cursor: "pointer",
                minHeight: "var(--touch-target)",
              }}
            >
              <Plus size={16} /> New Order
            </button>
          </div>

          {/* Legend */}
          <div style={{ display: "flex", gap: 20 }}>
            {[
              { label: "Available", color: "var(--color-success)" },
              { label: "Occupied",  color: "var(--color-warning)" },
              { label: "Reserved",  color: "var(--color-accent)" },
              { label: "Cleaning",  color: "var(--color-muted)" },
            ].map(({ label, color }) => (
              <div key={label} style={{
                display: "flex", alignItems: "center", gap: 6,
                fontFamily: "var(--font-mono)", fontSize: 11,
                color: "var(--color-muted)",
              }}>
                <div style={{
                  width: 8, height: 8, borderRadius: "50%",
                  background: color,
                }} />
                {label}
              </div>
            ))}
          </div>

          {/* Table tiles */}
          {tablesLoading ? (
            <TableGridSkeleton />
          ) : enrichedTables.length === 0 ? (
            <EmptyTables />
          ) : (
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
              gap: 12,
            }}>
              {enrichedTables.map((table) => (
                <TableTile
                  key={table.id}
                  table={table}
                  loading={createOrder.isPending}
                  onClick={() => handleTableClick(table)}
                />
              ))}
            </div>
          )}
        </div>

        {/* ── Open orders sidebar ──────────────────────────────────────────── */}
        <aside style={{
          borderLeft: "1px solid var(--color-border)",
          background: "var(--color-brand-2)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}>
          <div style={{
            padding: "14px 16px",
            borderBottom: "1px solid var(--color-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}>
            <span style={{
              fontFamily: "var(--font-display)",
              fontSize: 14, fontWeight: 700,
              color: "var(--color-text)",
            }}>
              Open Orders
            </span>
            <span style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: "var(--color-muted)",
              background: "var(--color-brand-3)",
              padding: "2px 8px",
              borderRadius: 20,
            }}>
              {openOrders.length}
            </span>
          </div>

          <div style={{ flex: 1, overflow: "auto", padding: "8px 8px" }}>
            {openOrders.length === 0 ? (
              <p style={{
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                color: "var(--color-muted)",
                textAlign: "center",
                marginTop: 32,
              }}>
                No open orders
              </p>
            ) : (
              openOrders.map((order: any) => (
                <OrderSidebarRow
                  key={order.id}
                  order={order}
                  onClick={() =>
                    navigate({ to: `/pos/order/${order.id}` })
                  }
                />
              ))
            )}
          </div>
        </aside>
      </div>

      {/* ── New order type modal ─────────────────────────────────────────── */}
      {orderTypeModal && (
        <div
          onClick={() => setOrderTypeModal(false)}
          style={{
            position: "fixed", inset: 0,
            background: "rgba(0,0,0,0.6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            zIndex: 50,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="animate-slide-up card"
            style={{ padding: 24, width: 320 }}
          >
            <h3 style={{
              fontFamily: "var(--font-display)",
              fontSize: 18, fontWeight: 700,
              color: "var(--color-text)",
              margin: "0 0 20px",
            }}>
              New Order
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <OrderTypeBtn
                label="Counter Sale"
                description="Quick sale at the counter"
                icon="🏪"
                onClick={() => handleNewOrder("counter")}
              />
              <OrderTypeBtn
                label="Takeaway"
                description="Order for collection"
                icon="🥡"
                onClick={() => handleNewOrder("takeaway")}
              />
              <p style={{
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                color: "var(--color-muted)",
                margin: "8px 0 0",
                textAlign: "center",
              }}>
                Or tap a table on the floor plan for dine-in
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── TableTile ────────────────────────────────────────────────────────────────
function TableTile({
  table,
  loading,
  onClick,
}: {
  table: EnrichedTable;
  loading: boolean;
  onClick: () => void;
}) {
  const isOverdue =
    table.orderOpenedAt &&
    Date.now() - new Date(table.orderOpenedAt).getTime() >
      ORDER_ALERT_MINUTES * 60 * 1000;

  const statusColor: Record<TableStatus, string> = {
    available: "var(--color-success)",
    occupied:  isOverdue ? "var(--color-danger)" : "var(--color-warning)",
    reserved:  "var(--color-accent)",
    cleaning:  "var(--color-muted)",
  };

  const statusLabel: Record<TableStatus, string> = {
    available: "Available",
    occupied:  isOverdue ? "Overdue" : "Occupied",
    reserved:  "Reserved",
    cleaning:  "Cleaning",
  };

  return (
    <button
      onClick={onClick}
      disabled={loading || table.status === "cleaning" || table.status === "reserved"}
      style={{
        padding: "16px 12px",
        background: "var(--color-brand-2)",
        border: `1px solid var(--color-border)`,
        borderRadius: "var(--radius-lg)",
        cursor: table.status === "available" || table.status === "occupied"
          ? "pointer" : "default",
        textAlign: "left",
        transition: "all 0.15s",
        position: "relative",
        minHeight: 100,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        borderLeft: `3px solid ${statusColor[table.status]}`,
        opacity: loading ? 0.6 : 1,
      }}
      onMouseEnter={(e) => {
        if (table.status === "available" || table.status === "occupied") {
          (e.currentTarget as HTMLElement).style.background = "var(--color-brand-3)";
        }
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.background = "var(--color-brand-2)";
      }}
    >
      <div>
        <div style={{
          fontFamily: "var(--font-display)",
          fontSize: 18, fontWeight: 700,
          color: "var(--color-text)",
        }}>
          {table.table_number}
        </div>
        {table.floor_zone && (
          <div style={{
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            color: "var(--color-muted)",
            marginTop: 2,
          }}>
            {table.floor_zone}
          </div>
        )}
      </div>

      <div>
        {/* Status badge */}
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 4,
          fontFamily: "var(--font-mono)",
          fontSize: 10,
          color: statusColor[table.status],
          marginBottom: table.orderOpenedAt ? 4 : 0,
        }}>
          <div style={{
            width: 6, height: 6, borderRadius: "50%",
            background: statusColor[table.status],
          }} />
          {statusLabel[table.status]}
        </div>

        {/* Order info */}
        {table.orderOpenedAt && (
          <div style={{
            fontFamily: "var(--font-mono)", fontSize: 10,
            color: isOverdue ? "var(--color-danger)" : "var(--color-muted)",
          }}>
            {formatDistanceToNow(new Date(table.orderOpenedAt), { addSuffix: true })}
          </div>
        )}
        {table.totalAmount && parseFloat(table.totalAmount) > 0 && (
          <div style={{
            fontFamily: "var(--font-mono)",
            fontSize: 12, fontWeight: 500,
            color: "var(--color-text)",
            marginTop: 2,
          }}>
            {fmt(table.totalAmount)}
          </div>
        )}
      </div>
    </button>
  );
}

// ─── OrderSidebarRow ──────────────────────────────────────────────────────────
function OrderSidebarRow({
  order,
  onClick,
}: {
  order: any;
  onClick: () => void;
}) {
  const label = order.table
    ? `Table ${order.table.table_number}`
    : order.order_type === "counter"
    ? "Counter"
    : "Takeaway";

  const statusColor =
    order.status === "sent" ? "var(--color-accent)" : "var(--color-muted)";

  return (
    <button
      onClick={onClick}
      style={{
        width: "100%",
        padding: "10px 12px",
        background: "transparent",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-md)",
        marginBottom: 6,
        cursor: "pointer",
        textAlign: "left",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 8,
        transition: "background 0.1s",
        minHeight: "var(--touch-target)",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.background = "var(--color-brand-3)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.background = "transparent";
      }}
    >
      <div>
        <div style={{
          fontFamily: "var(--font-body)",
          fontSize: 13, fontWeight: 500,
          color: "var(--color-text)",
        }}>
          {label}
        </div>
        <div style={{
          fontFamily: "var(--font-mono)",
          fontSize: 10,
          color: statusColor,
          marginTop: 2,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}>
          {order.status}
        </div>
      </div>
      <div style={{
        fontFamily: "var(--font-mono)",
        fontSize: 12, fontWeight: 500,
        color: "var(--color-text)",
      }}>
        {fmt(order.total_amount ?? "0")}
      </div>
    </button>
  );
}

// ─── NavBtn ───────────────────────────────────────────────────────────────────
function NavBtn({
  icon, label, to,
}: {
  icon: React.ReactNode;
  label: string;
  to: string;
}) {
  return (
    <Link to={to} style={{ textDecoration: "none" }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 5,
        padding: "6px 10px",
        borderRadius: "var(--radius-sm)",
        background: "transparent",
        color: "var(--color-muted)",
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        cursor: "pointer",
        transition: "all 0.15s",
        letterSpacing: "0.04em",
      }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLElement).style.background = "var(--color-brand-3)";
          (e.currentTarget as HTMLElement).style.color = "var(--color-text)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLElement).style.background = "transparent";
          (e.currentTarget as HTMLElement).style.color = "var(--color-muted)";
        }}
      >
        {icon} {label}
      </div>
    </Link>
  );
}

// ─── OrderTypeBtn ─────────────────────────────────────────────────────────────
function OrderTypeBtn({
  label, description, icon, onClick,
}: {
  label: string; description: string; icon: string; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", gap: 14,
        padding: "14px 16px",
        background: "var(--color-brand-3)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-md)",
        cursor: "pointer",
        textAlign: "left",
        width: "100%",
        transition: "border-color 0.15s",
        minHeight: "var(--touch-target)",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = "var(--color-accent)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = "var(--color-border)";
      }}
    >
      <span style={{ fontSize: 24 }}>{icon}</span>
      <div>
        <div style={{
          fontFamily: "var(--font-display)",
          fontSize: 15, fontWeight: 700,
          color: "var(--color-text)",
        }}>
          {label}
        </div>
        <div style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          color: "var(--color-muted)",
          marginTop: 2,
        }}>
          {description}
        </div>
      </div>
    </button>
  );
}

// ─── Skeleton / Empty states ──────────────────────────────────────────────────
function TableGridSkeleton() {
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
      gap: 12,
    }}>
      {Array.from({ length: 12 }).map((_, i) => (
        <div
          key={i}
          style={{
            height: 100,
            borderRadius: "var(--radius-lg)",
            background: "var(--color-brand-2)",
            animation: "pulse 1.5s ease-in-out infinite",
            animationDelay: `${i * 0.05}s`,
          }}
        />
      ))}
    </div>
  );
}

function EmptyTables() {
  return (
    <div style={{
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      padding: 48, gap: 12,
    }}>
      <span style={{ fontSize: 40, opacity: 0.4 }}>🪑</span>
      <p style={{
        fontFamily: "var(--font-body)",
        fontSize: 15, color: "var(--color-muted)",
        margin: 0,
      }}>
        No tables configured yet
      </p>
      <p style={{
        fontFamily: "var(--font-mono)",
        fontSize: 11, color: "var(--color-muted)",
        margin: 0,
      }}>
        Add tables in Settings → Floor Plan
      </p>
    </div>
  );
}