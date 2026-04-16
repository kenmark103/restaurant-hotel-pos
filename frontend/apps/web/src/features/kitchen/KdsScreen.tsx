/**
 * KDS Screen — Kitchen Display System
 * File: apps/web/src/features/kitchen/KdsScreen.tsx
 *
 * Full-screen, no nav chrome. Designed for wall-mounted tablets.
 * Real-time via WebSocket — tickets update without polling.
 * Roles: kitchen, kitchen_manager, manager, admin
 */
import { useState, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSessionStore } from "@restaurantos/stores";
import { kitchenApi, settingsApi } from "@restaurantos/api";
import { connectSocket, joinKitchenRoom, leaveKitchenRoom } from "@/lib/socket";
import { KdsLayout } from "@/layouts/PosLayout";
import { formatDistanceToNow, differenceInSeconds } from "date-fns";
import { Wifi, WifiOff, Clock, Zap, ChefHat, CheckCircle2 } from "lucide-react";

// ─── Types (backend returns these shapes) ─────────────────────────────────────
interface KdsTicket {
  id: number;
  order_id: number;
  order_number?: string;
  table_label?: string | null;     // "Table 4" | "Counter" | "Takeaway"
  station_id: string;
  station_name: string;
  status: "pending" | "preparing" | "ready" | "served" | "cancelled";
  is_rush: boolean;
  sent_at: string;                 // ISO datetime
  started_at?: string | null;
  ready_at?: string | null;
  estimated_prep_seconds?: number; // from menu item prep_time_minutes → seconds
  items: KdsTicketItem[];
}

interface KdsTicketItem {
  id: number;
  name: string;
  quantity: number;
  variant_name?: string | null;
  modifiers: string[];             // option names
  note?: string | null;
}

// ─── Constants ────────────────────────────────────────────────────────────────
const POLL_INTERVAL_MS  = 30_000; // fallback poll (WS should handle updates)
const AMBER_MULTIPLIER  = 1.0;    // past estimated prep time → amber
const RED_MULTIPLIER    = 2.0;    // 2× estimated prep time → red/overdue

const STATUS_NEXT: Record<KdsTicket["status"], KdsTicket["status"] | null> = {
  pending:   "preparing",
  preparing: "ready",
  ready:     "served",
  served:    null,
  cancelled: null,
};

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function KdsScreen() {
  const { branchId, token, role } = useSessionStore((s) => ({
    branchId: s.branchId,
    token: s.token,
    role: s.role,
  }));

  const [activeStationId, setActiveStationId] = useState<string | "all">("all");
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [now, setNow] = useState(Date.now());
  const qc = useQueryClient();

  // ── Stations ──────────────────────────────────────────────────────────────
  const { data: productConfig } = useQuery({
    queryKey: ["product-config"],
    queryFn: settingsApi.getProductConfiguration,
    staleTime: 1000 * 60 * 30,
  });
  const stations = productConfig?.stations ?? [];

  // ── Tickets ───────────────────────────────────────────────────────────────
  const { data: tickets = [], isLoading } = useQuery({
    queryKey: ["kds-tickets", branchId, activeStationId],
    queryFn: () =>
      kitchenApi.listTickets({
        branch_id: branchId!,
        station_id: activeStationId === "all" ? undefined : activeStationId,
        status: "pending,preparing",
      }) as Promise<KdsTicket[]>,
    enabled: !!branchId,
    staleTime: 1000 * 5,
    refetchInterval: POLL_INTERVAL_MS,
  });

  // ── Mutations ─────────────────────────────────────────────────────────────
  const bumpMutation = useMutation({
    mutationFn: ({ ticketId, status }: { ticketId: number; status: string }) =>
      kitchenApi.updateTicketStatus(ticketId, { status }),
    onMutate: async ({ ticketId, status }) => {
      // Optimistic update — flip status immediately
      await qc.cancelQueries({ queryKey: ["kds-tickets"] });
      const prev = qc.getQueryData<KdsTicket[]>(["kds-tickets", branchId, activeStationId]);
      qc.setQueryData<KdsTicket[]>(
        ["kds-tickets", branchId, activeStationId],
        (old = []) =>
          status === "served" || status === "cancelled"
            ? old.filter((t) => t.id !== ticketId)
            : old.map((t) =>
                t.id === ticketId
                  ? { ...t, status: status as KdsTicket["status"] }
                  : t
              )
      );
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) {
        qc.setQueryData(["kds-tickets", branchId, activeStationId], ctx.prev);
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["kds-tickets"] });
    },
  });

  const rushMutation = useMutation({
    mutationFn: (ticketId: number) => kitchenApi.rushTicket(ticketId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kds-tickets"] }),
  });

  // ── WebSocket: join/leave kitchen rooms ───────────────────────────────────
  useEffect(() => {
    if (!token || !branchId) return;
    connectSocket(token, branchId);

    if (activeStationId === "all") {
      // Join all station rooms
      stations.forEach((s) => joinKitchenRoom(branchId, s.id));
    } else {
      joinKitchenRoom(branchId, activeStationId);
    }

    return () => {
      if (activeStationId === "all") {
        stations.forEach((s) => leaveKitchenRoom(branchId, s.id));
      } else {
        leaveKitchenRoom(branchId, activeStationId);
      }
    };
  }, [token, branchId, activeStationId, stations]);

  // ── Live timer (updates every second for elapsed time colours) ────────────
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  // ── Online/offline ────────────────────────────────────────────────────────
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

  // ── Handlers ─────────────────────────────────────────────────────────────
  const handleBump = useCallback((ticket: KdsTicket) => {
    const next = STATUS_NEXT[ticket.status];
    if (!next) return;
    bumpMutation.mutate({ ticketId: ticket.id, status: next });
  }, [bumpMutation]);

  const handleRush = useCallback((ticket: KdsTicket, e: React.MouseEvent) => {
    e.stopPropagation();
    rushMutation.mutate(ticket.id);
  }, [rushMutation]);

  // Sort: RUSH first, then by sent_at ascending (oldest first)
  const sorted = [...tickets].sort((a, b) => {
    if (a.is_rush !== b.is_rush) return a.is_rush ? -1 : 1;
    return new Date(a.sent_at).getTime() - new Date(b.sent_at).getTime();
  });

  const pendingCount   = tickets.filter((t) => t.status === "pending").length;
  const preparingCount = tickets.filter((t) => t.status === "preparing").length;

  const canRush = role === "kitchen_manager" || role === "manager" || role === "admin";

  return (
    <KdsLayout
      statusBar={
        <KdsStatusBar
          stations={stations}
          activeStationId={activeStationId}
          onStationChange={setActiveStationId}
          pendingCount={pendingCount}
          preparingCount={preparingCount}
          isOnline={isOnline}
        />
      }
    >
      {isLoading ? (
        <KdsSkeleton />
      ) : sorted.length === 0 ? (
        <KdsEmpty />
      ) : (
        <div style={{
          height: "100%",
          overflowY: "auto",
          padding: 12,
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: 12,
          alignContent: "start",
        }}>
          {sorted.map((ticket) => (
            <TicketCard
              key={ticket.id}
              ticket={ticket}
              now={now}
              onBump={handleBump}
              onRush={canRush ? handleRush : undefined}
              bumping={bumpMutation.isPending}
            />
          ))}
        </div>
      )}
    </KdsLayout>
  );
}

// ─── KdsStatusBar ─────────────────────────────────────────────────────────────
function KdsStatusBar({
  stations, activeStationId, onStationChange,
  pendingCount, preparingCount, isOnline,
}: {
  stations: { id: string; name: string; color: string }[];
  activeStationId: string;
  onStationChange: (id: string) => void;
  pendingCount: number;
  preparingCount: number;
  isOnline: boolean;
}) {
  // Live clock
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <>
      {/* Logo */}
      <ChefHat size={16} style={{ color: "var(--color-accent)", flexShrink: 0 }} />

      {/* Station tabs */}
      <div style={{ display: "flex", gap: 4, overflow: "auto" }}>
        <StationTab
          label="All"
          active={activeStationId === "all"}
          color="var(--color-muted)"
          onClick={() => onStationChange("all")}
        />
        {stations.map((s) => (
          <StationTab
            key={s.id}
            label={s.name}
            active={activeStationId === s.id}
            color={s.color}
            onClick={() => onStationChange(s.id)}
          />
        ))}
      </div>

      <div style={{ flex: 1 }} />

      {/* Counts */}
      <div style={{ display: "flex", gap: 12, flexShrink: 0 }}>
        <CountBadge
          label="Pending"
          count={pendingCount}
          color="var(--color-muted)"
        />
        <CountBadge
          label="Preparing"
          count={preparingCount}
          color="var(--color-accent)"
        />
      </div>

      {/* Clock */}
      <div style={{
        fontFamily: "var(--font-mono)",
        fontSize: 13, fontWeight: 500,
        color: "var(--color-text)",
        flexShrink: 0,
        paddingLeft: 12,
        borderLeft: "1px solid var(--color-border)",
      }}>
        {time.toLocaleTimeString("en-KE", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
      </div>

      {/* Online */}
      <div style={{
        flexShrink: 0,
        color: isOnline ? "var(--color-success)" : "var(--color-danger)",
        lineHeight: 0,
      }}>
        {isOnline ? <Wifi size={14} /> : <WifiOff size={14} />}
      </div>
    </>
  );
}

function StationTab({
  label, active, color, onClick,
}: {
  label: string; active: boolean; color: string; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "4px 12px",
        borderRadius: 20,
        border: "1px solid",
        borderColor: active ? color : "var(--color-border)",
        background: active ? `${color}22` : "transparent",
        color: active ? color : "var(--color-muted)",
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        cursor: "pointer",
        whiteSpace: "nowrap",
        transition: "all 0.15s",
        minHeight: "var(--touch-target)",
      }}
    >
      {label}
    </button>
  );
}

function CountBadge({
  label, count, color,
}: {
  label: string; count: number; color: string;
}) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 5,
      fontFamily: "var(--font-mono)", fontSize: 11,
      color: "var(--color-muted)",
    }}>
      <span style={{
        fontFamily: "var(--font-display)",
        fontSize: 15, fontWeight: 700,
        color,
      }}>
        {count}
      </span>
      {label}
    </div>
  );
}

// ─── TicketCard ───────────────────────────────────────────────────────────────
function TicketCard({
  ticket, now, onBump, onRush, bumping,
}: {
  ticket: KdsTicket;
  now: number;
  onBump: (t: KdsTicket) => void;
  onRush?: (t: KdsTicket, e: React.MouseEvent) => void;
  bumping: boolean;
}) {
  const sentAt   = new Date(ticket.sent_at).getTime();
  const elapsedS = Math.floor((now - sentAt) / 1000);
  const estimatedS = ticket.estimated_prep_seconds ?? 10 * 60; // default 10min

  const isAmber  = elapsedS >= estimatedS * AMBER_MULTIPLIER;
  const isRed    = elapsedS >= estimatedS * RED_MULTIPLIER;

  // Card colour class based on status + timing
  const cardClass =
    ticket.is_rush ? "kds-rush"
    : ticket.status === "preparing" ? "kds-preparing"
    : ticket.status === "ready"     ? "kds-ready"
    : isRed                         ? "kds-overdue"
    : "kds-pending";

  const timerColor =
    isRed    ? "var(--color-danger)"
    : isAmber  ? "var(--color-warning)"
    : ticket.status === "preparing" ? "var(--color-accent)"
    : ticket.status === "ready"     ? "var(--color-success)"
    : "var(--color-muted)";

  const nextStatus = STATUS_NEXT[ticket.status];
  const bumpLabel =
    ticket.status === "pending"   ? "Start" :
    ticket.status === "preparing" ? "Ready" :
    ticket.status === "ready"     ? "Served" : null;

  return (
    <div
      className={`${cardClass} animate-fade-in`}
      style={{
        borderRadius: "var(--radius-lg)",
        padding: 0,
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        minHeight: 160,
        // Rush pulse animation
        animation: ticket.is_rush
          ? "pulse-glow 1.5s ease-in-out infinite, fadeIn 0.2s ease both"
          : "fadeIn 0.2s ease both",
      }}
    >
      {/* ── Card header ──────────────────────────────────────────────────── */}
      <div style={{
        padding: "10px 14px 8px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 8,
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {/* Order label */}
          <span style={{
            fontFamily: "var(--font-display)",
            fontSize: 16, fontWeight: 800,
            color: "var(--color-text)",
            letterSpacing: "-0.5px",
          }}>
            {ticket.table_label ?? `#${ticket.order_id}`}
          </span>

          {/* RUSH badge */}
          {ticket.is_rush && (
            <span style={{
              padding: "2px 7px",
              background: "var(--color-danger)",
              borderRadius: 4,
              fontFamily: "var(--font-display)",
              fontSize: 10, fontWeight: 700,
              color: "#fff",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}>
              RUSH
            </span>
          )}
        </div>

        {/* Timer */}
        <div style={{
          display: "flex", alignItems: "center", gap: 4,
          fontFamily: "var(--font-mono)",
          fontSize: 13, fontWeight: 500,
          color: timerColor,
        }}>
          <Clock size={12} />
          {formatElapsed(elapsedS)}
        </div>
      </div>

      {/* ── Items ────────────────────────────────────────────────────────── */}
      <div style={{
        flex: 1,
        padding: "10px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}>
        {ticket.items.map((item) => (
          <div key={item.id}>
            <div style={{
              display: "flex",
              alignItems: "baseline",
              gap: 8,
            }}>
              {/* Quantity */}
              <span style={{
                fontFamily: "var(--font-display)",
                fontSize: 22, fontWeight: 800,
                color: "var(--color-accent-2)",
                lineHeight: 1,
                flexShrink: 0,
                minWidth: 28,
              }}>
                {item.quantity}×
              </span>
              {/* Name */}
              <span style={{
                fontFamily: "var(--font-body)",
                fontSize: 16, fontWeight: 500,
                color: "var(--color-text)",
                lineHeight: 1.3,
              }}>
                {item.name}
                {item.variant_name && (
                  <span style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    color: "var(--color-muted)",
                    marginLeft: 6,
                  }}>
                    ({item.variant_name})
                  </span>
                )}
              </span>
            </div>

            {/* Modifiers */}
            {item.modifiers.length > 0 && (
              <div style={{
                marginLeft: 36,
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                color: "var(--color-muted-2)",
                marginTop: 2,
              }}>
                + {item.modifiers.join(", ")}
              </div>
            )}

            {/* Note */}
            {item.note && (
              <div style={{
                marginLeft: 36,
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                color: "var(--color-warning)",
                marginTop: 2,
              }}>
                ⚠ {item.note}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* ── Footer: bump button + rush ────────────────────────────────────── */}
      <div style={{
        padding: "10px 12px",
        display: "flex",
        gap: 8,
        borderTop: "1px solid rgba(255,255,255,0.06)",
      }}>
        {/* Rush button (managers only) */}
        {onRush && ticket.status !== "ready" && ticket.status !== "served" && !ticket.is_rush && (
          <button
            onClick={(e) => onRush(ticket, e)}
            style={{
              padding: "8px 12px",
              background: "rgba(239,68,68,0.15)",
              border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: "var(--radius-sm)",
              color: "var(--color-danger)",
              fontFamily: "var(--font-mono)",
              fontSize: 11, cursor: "pointer",
              display: "flex", alignItems: "center", gap: 4,
              flexShrink: 0,
              minHeight: "var(--touch-target)",
            }}
          >
            <Zap size={12} /> Rush
          </button>
        )}

        {/* Bump button */}
        {bumpLabel && (
          <button
            onClick={() => onBump(ticket)}
            disabled={bumping}
            style={{
              flex: 1,
              padding: "10px",
              background:
                ticket.status === "pending"   ? "var(--color-accent)"
                : ticket.status === "preparing" ? "var(--color-success)"
                : "rgba(100,116,139,0.3)",
              border: "none",
              borderRadius: "var(--radius-md)",
              color: "#fff",
              fontFamily: "var(--font-display)",
              fontSize: 14, fontWeight: 700,
              cursor: bumping ? "not-allowed" : "pointer",
              opacity: bumping ? 0.6 : 1,
              display: "flex", alignItems: "center", justifyContent: "center",
              gap: 6,
              minHeight: "var(--touch-target)",
              transition: "opacity 0.15s",
            }}
          >
            <CheckCircle2 size={15} />
            {bumpLabel}
          </button>
        )}
      </div>
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function KdsSkeleton() {
  return (
    <div style={{
      padding: 12,
      display: "grid",
      gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
      gap: 12,
    }}>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} style={{
          height: 200,
          borderRadius: "var(--radius-lg)",
          background: "var(--color-brand-2)",
          opacity: 0.5,
        }} />
      ))}
    </div>
  );
}

function KdsEmpty() {
  return (
    <div style={{
      height: "100%",
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      gap: 12,
    }}>
      <ChefHat size={48} style={{ color: "var(--color-muted)", opacity: 0.4 }} />
      <p style={{
        fontFamily: "var(--font-display)",
        fontSize: 20, fontWeight: 700,
        color: "var(--color-muted)",
        margin: 0,
      }}>
        No active tickets
      </p>
      <p style={{
        fontFamily: "var(--font-mono)",
        fontSize: 12,
        color: "var(--color-muted)",
        margin: 0, opacity: 0.6,
      }}>
        New orders will appear here in real-time
      </p>
    </div>
  );
}