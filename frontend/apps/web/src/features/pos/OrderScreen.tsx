import { useState, useMemo, useRef, useEffect } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import {
  useOrder, useMenu, useAddItem, useVoidItem,
  useSendToKitchen, useCloseOrder, useProductConfig
} from "@/hooks/useApi";
import {
  useCartStore, useSessionStore, useUiStore, can
} from "@restaurantos/stores";
import { posApi, type CategoryRead, type MenuItemRead } from "@restaurantos/api";
import { PosLayout } from "@/layouts/PosLayout";
import { fmt, cn } from "@/lib/cn";
import {
  ArrowLeft, Search, Send, CreditCard, SplitSquareVertical,
  Minus, Plus, X, ChefHat, Trash2, Percent, MoreHorizontal,
  ShoppingCart, Receipt
} from "lucide-react";
import { PaymentModal } from "./PaymentModal";

// ─── Helpers ──────────────────────────────────────────────────────────────────
function isAvailableNow(category: CategoryRead): boolean {
  if (!category.available_from || !category.available_until) return true;
  const now = new Date();
  const hhmm = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  return hhmm >= category.available_from && hhmm <= category.available_until;
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function OrderScreen() {
  const params = useParams({ from: "/pos/order/$orderId" });
  const orderId = parseInt(params.orderId, 10);
  const navigate = useNavigate();
  const { role } = useSessionStore((s) => ({ role: s.role }));

  // Data
  const { data: order, isLoading: orderLoading } = useOrder(orderId);
  const { data: categories = [] } = useMenu();
  const { data: productConfig } = useProductConfig();
  const hydrateFromOrder = useCartStore((s) => s.hydrateFromOrder);

  // UI state
  const [activeCategoryId, setActiveCategoryId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [sendStationFilter, setSendStationFilter] = useState<string | undefined>();
  const [showStationPicker, setShowStationPicker] = useState(false);

  // Mutations
  const addItem      = useAddItem(orderId);
  const voidItem     = useVoidItem(orderId);
  const sendKitchen  = useSendToKitchen(orderId);
  const closeOrder   = useCloseOrder(orderId);

  // Hydrate cart when order loads
  useEffect(() => {
    if (order) hydrateFromOrder(order);
  }, [order, hydrateFromOrder]);

  // Auto-select first available category
  useEffect(() => {
    if (categories.length > 0 && !activeCategoryId) {
      const first = categories.find(isAvailableNow);
      if (first) setActiveCategoryId(first.id);
    }
  }, [categories, activeCategoryId]);

  const activeCategory = categories.find((c) => c.id === activeCategoryId);

  // Search across all items
  const searchResults: MenuItemRead[] = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase();
    return categories
      .flatMap((c) => c.items)
      .filter(
        (item) =>
          item.is_available &&
          (item.name.toLowerCase().includes(q) ||
            item.sku?.toLowerCase().includes(q) ||
            item.barcode?.toLowerCase().includes(q))
      )
      .slice(0, 20);
  }, [searchQuery, categories]);

  const displayItems: MenuItemRead[] = searchQuery
    ? searchResults
    : (activeCategory?.items ?? []).filter((i) => i.is_available);

  const activeItems = (order?.items ?? []).filter((i) => !i.is_voided);
  const hasUnsent = activeItems.some((i) => !i.sent_to_kitchen);
  const orderClosed = order?.status === "closed" || order?.status === "voided";

  const stations = productConfig?.stations ?? [];

  const handleAddItem = (item: MenuItemRead) => {
    if (orderClosed) return;
    addItem.mutate({ menu_item_id: item.id, quantity: 1 });
  };

  const handleSend = () => {
    if (stations.length > 1) {
      setShowStationPicker(true);
    } else {
      sendKitchen.mutate(undefined);
    }
  };

  const handleSendToStation = (stationId?: string) => {
    setShowStationPicker(false);
    sendKitchen.mutate(stationId);
  };

  const orderLabel = order?.table
    ? `Table ${order.table.table_number}`
    : order?.order_type === "counter"
    ? "Counter"
    : "Takeaway";

  return (
    <PosLayout
      topBar={
        <TopBar
          label={orderLabel}
          orderId={orderId}
          status={order?.status}
          onBack={() => navigate({ to: "/pos" })}
        />
      }
      left={
        <MenuPanel
          categories={categories}
          activeCategoryId={activeCategoryId}
          onCategoryChange={setActiveCategoryId}
          displayItems={displayItems}
          onAddItem={handleAddItem}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          adding={addItem.isPending}
        />
      }
      center={
        <CartPanel
          order={order}
          loading={orderLoading}
          onVoidItem={(itemId, reason) =>
            voidItem.mutate({ itemId, reason })
          }
          canVoid={can(role, "void_item")}
        />
      }
      right={
        <ActionsPanel
          order={order}
          hasUnsent={hasUnsent}
          orderClosed={orderClosed}
          onSend={handleSend}
          sending={sendKitchen.isPending}
          onPay={() => setPaymentModalOpen(true)}
          canVoidOrder={can(role, "void_order")}
          canDiscount={can(role, "apply_discount")}
        />
      }
    />
  );

  return (
    <>
      {paymentModalOpen && order && (
        <PaymentModal
          order={order}
          onClose={() => setPaymentModalOpen(false)}
          onSuccess={() => {
            setPaymentModalOpen(false);
            navigate({ to: "/pos" });
          }}
        />
      )}
      {showStationPicker && (
        <StationPickerModal
          stations={stations}
          onSelect={handleSendToStation}
          onClose={() => setShowStationPicker(false)}
        />
      )}
    </>
  );
}

// ─── TopBar ───────────────────────────────────────────────────────────────────
function TopBar({
  label, orderId, status, onBack,
}: {
  label: string; orderId: number; status?: string; onBack: () => void;
}) {
  const statusColor = status === "sent" ? "var(--color-accent)"
    : status === "closed" ? "var(--color-success)"
    : status === "voided" ? "var(--color-danger)"
    : "var(--color-muted)";

  return (
    <>
      <button
        onClick={onBack}
        style={{
          display: "flex", alignItems: "center", gap: 6,
          background: "none", border: "none",
          color: "var(--color-muted)", cursor: "pointer",
          fontFamily: "var(--font-mono)", fontSize: 12,
          padding: "6px 8px", borderRadius: 6,
          minHeight: "var(--touch-target)",
        }}
      >
        <ArrowLeft size={14} /> Floor
      </button>

      <div style={{
        fontFamily: "var(--font-display)",
        fontSize: 15, fontWeight: 700,
        color: "var(--color-text)",
      }}>
        {label}
      </div>

      <div style={{
        fontFamily: "var(--font-mono)",
        fontSize: 10,
        color: statusColor,
        textTransform: "uppercase",
        letterSpacing: "0.1em",
        padding: "3px 8px",
        background: `${statusColor}20`,
        borderRadius: 4,
      }}>
        {status ?? "open"}
      </div>

      <div style={{
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        color: "var(--color-muted)",
        marginLeft: 4,
      }}>
        #{orderId}
      </div>
    </>
  );
}

// ─── MenuPanel ────────────────────────────────────────────────────────────────
function MenuPanel({
  categories, activeCategoryId, onCategoryChange,
  displayItems, onAddItem, searchQuery, onSearchChange, adding,
}: {
  categories: CategoryRead[];
  activeCategoryId: number | null;
  onCategoryChange: (id: number) => void;
  displayItems: MenuItemRead[];
  onAddItem: (item: MenuItemRead) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  adding: boolean;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Search bar */}
      <div style={{
        padding: "12px 12px 8px",
        borderBottom: "1px solid var(--color-border)",
      }}>
        <div style={{ position: "relative" }}>
          <Search
            size={14}
            style={{
              position: "absolute", left: 10,
              top: "50%", transform: "translateY(-50%)",
              color: "var(--color-muted)",
              pointerEvents: "none",
            }}
          />
          <input
            type="text"
            placeholder="Search menu or scan barcode..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            style={{
              width: "100%",
              padding: "9px 10px 9px 30px",
              background: "var(--color-brand-2)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              color: "var(--color-text)",
              fontFamily: "var(--font-body)",
              fontSize: 13,
              outline: "none",
            }}
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange("")}
              style={{
                position: "absolute", right: 8, top: "50%",
                transform: "translateY(-50%)",
                background: "none", border: "none",
                color: "var(--color-muted)", cursor: "pointer",
                lineHeight: 0, padding: 2,
              }}
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Category tabs */}
      {!searchQuery && (
        <div style={{
          display: "flex",
          gap: 6,
          padding: "8px 12px",
          overflowX: "auto",
          borderBottom: "1px solid var(--color-border)",
          flexShrink: 0,
        }}>
          {categories.filter(isAvailableNow).map((cat) => (
            <button
              key={cat.id}
              onClick={() => onCategoryChange(cat.id)}
              style={{
                padding: "7px 14px",
                borderRadius: 20,
                border: "1px solid",
                borderColor:
                  activeCategoryId === cat.id
                    ? "var(--color-accent)"
                    : "var(--color-border)",
                background:
                  activeCategoryId === cat.id
                    ? "rgba(59,130,246,0.15)"
                    : "transparent",
                color:
                  activeCategoryId === cat.id
                    ? "var(--color-accent-2)"
                    : "var(--color-muted)",
                fontFamily: "var(--font-body)",
                fontSize: 13, fontWeight: activeCategoryId === cat.id ? 500 : 400,
                cursor: "pointer",
                whiteSpace: "nowrap",
                transition: "all 0.15s",
                flexShrink: 0,
                minHeight: "var(--touch-target)",
              }}
            >
              {cat.name}
            </button>
          ))}
        </div>
      )}

      {/* Item grid */}
      <div style={{
        flex: 1, overflow: "auto",
        padding: 12,
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(var(--tile-min), 1fr))",
        gap: 10,
        alignContent: "start",
      }}>
        {displayItems.map((item) => (
          <MenuItemTile
            key={item.id}
            item={item}
            onPress={() => onAddItem(item)}
            disabled={adding}
          />
        ))}
        {displayItems.length === 0 && (
          <div style={{
            gridColumn: "1/-1",
            textAlign: "center", padding: "32px 16px",
            fontFamily: "var(--font-mono)",
            fontSize: 12, color: "var(--color-muted)",
          }}>
            {searchQuery ? "No items match your search" : "No items in this category"}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── MenuItemTile ─────────────────────────────────────────────────────────────
function MenuItemTile({
  item, onPress, disabled,
}: {
  item: MenuItemRead; onPress: () => void; disabled?: boolean;
}) {
  const [pressed, setPressed] = useState(false);

  return (
    <button
      type="button"
      disabled={disabled}
      onPointerDown={() => setPressed(true)}
      onPointerUp={() => { setPressed(false); if (!disabled) onPress(); }}
      onPointerLeave={() => setPressed(false)}
      style={{
        minHeight: "var(--tile-min)",
        padding: 12,
        borderRadius: "var(--radius-md)",
        background: pressed ? "var(--color-brand-3)" : "var(--color-brand-2)",
        border: "1px solid var(--color-border)",
        cursor: disabled ? "not-allowed" : "pointer",
        textAlign: "left",
        transform: pressed ? "scale(0.96)" : "scale(1)",
        transition: "all 0.1s ease",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        gap: 6,
        outline: "none",
        WebkitTapHighlightColor: "transparent",
      }}
    >
      {/* Item image */}
      {item.image_url ? (
        <img
          src={item.image_url}
          alt={item.name}
          style={{
            width: "100%", height: 60,
            objectFit: "cover",
            borderRadius: 6,
            marginBottom: 4,
          }}
        />
      ) : (
        <div style={{
          width: "100%", height: 44,
          background: "var(--color-brand-3)",
          borderRadius: 6,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 20, marginBottom: 4,
        }}>
          🍽️
        </div>
      )}

      <div style={{
        fontFamily: "var(--font-body)",
        fontSize: 13, fontWeight: 500,
        color: "var(--color-text)",
        lineHeight: 1.3,
      }}>
        {item.name}
      </div>
      <div style={{
        fontFamily: "var(--font-mono)",
        fontSize: 13, fontWeight: 500,
        color: "var(--color-accent-2)",
      }}>
        {fmt(item.base_price)}
      </div>
    </button>
  );
}

// ─── CartPanel ────────────────────────────────────────────────────────────────
function CartPanel({
  order, loading, onVoidItem, canVoid,
}: {
  order: ReturnType<typeof useOrder>["data"];
  loading: boolean;
  onVoidItem: (itemId: number, reason: string) => void;
  canVoid: boolean;
}) {
  const items = order?.items ?? [];
  const activeItems = items.filter((i) => !i.is_voided);

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100%",
    }}>
      {/* Cart header */}
      <div style={{
        padding: "12px 14px",
        borderBottom: "1px solid var(--color-border)",
        display: "flex",
        alignItems: "center",
        gap: 8,
        flexShrink: 0,
      }}>
        <ShoppingCart size={15} style={{ color: "var(--color-muted)" }} />
        <span style={{
          fontFamily: "var(--font-display)",
          fontSize: 14, fontWeight: 700,
          color: "var(--color-text)",
        }}>
          Cart
        </span>
        <span style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          color: "var(--color-muted)",
          background: "var(--color-brand)",
          padding: "1px 7px",
          borderRadius: 10,
        }}>
          {activeItems.length}
        </span>
      </div>

      {/* Items */}
      <div style={{ flex: 1, overflow: "auto", padding: "8px 10px" }}>
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} style={{
              height: 56, borderRadius: 8,
              background: "var(--color-brand-3)",
              marginBottom: 8,
              opacity: 0.5,
            }} />
          ))
        ) : activeItems.length === 0 ? (
          <div style={{
            textAlign: "center", padding: "48px 16px",
            fontFamily: "var(--font-mono)",
            fontSize: 12, color: "var(--color-muted)",
          }}>
            No items yet.{"\n"}Tap a menu item to add.
          </div>
        ) : (
          activeItems.map((item) => (
            <CartItemRow
              key={item.id}
              item={item}
              onVoid={canVoid ? () => onVoidItem(item.id, "Cashier void") : undefined}
            />
          ))
        )}

        {/* Voided items — dimmed */}
        {items
          .filter((i) => i.is_voided)
          .map((item) => (
            <div
              key={item.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "8px 10px",
                opacity: 0.35,
                textDecoration: "line-through",
              }}
            >
              <span style={{
                fontFamily: "var(--font-body)", fontSize: 13,
                color: "var(--color-text)", flex: 1,
              }}>
                {item.menu_item_name}
              </span>
              <span style={{
                fontFamily: "var(--font-mono)", fontSize: 11,
                color: "var(--color-danger)",
              }}>
                VOID
              </span>
            </div>
          ))}
      </div>

      {/* Totals */}
      {order && (
        <div style={{
          padding: "12px 14px",
          borderTop: "1px solid var(--color-border)",
          flexShrink: 0,
        }}>
          <TotalRow label="Subtotal" value={order.subtotal} />
          {parseFloat(order.discount_total) > 0 && (
            <TotalRow
              label="Discount"
              value={`-${order.discount_total}`}
              valueColor="var(--color-success)"
            />
          )}
          <TotalRow label="Tax" value={order.tax_amount} />
          <div style={{
            height: 1, background: "var(--color-border)",
            margin: "8px 0",
          }} />
          <TotalRow
            label="TOTAL"
            value={order.total_amount}
            bold
            valueStyle={{ fontFamily: "var(--font-mono)", fontSize: 18 }}
          />
        </div>
      )}
    </div>
  );
}

function TotalRow({
  label, value, bold, valueColor, valueStyle,
}: {
  label: string; value: string; bold?: boolean;
  valueColor?: string; valueStyle?: React.CSSProperties;
}) {
  return (
    <div style={{
      display: "flex",
      justifyContent: "space-between",
      marginBottom: 4,
    }}>
      <span style={{
        fontFamily: "var(--font-mono)",
        fontSize: bold ? 12 : 11,
        fontWeight: bold ? 700 : 400,
        color: bold ? "var(--color-text)" : "var(--color-muted)",
        letterSpacing: "0.06em",
        textTransform: "uppercase",
      }}>
        {label}
      </span>
      <span style={{
        fontFamily: "var(--font-mono)",
        fontSize: bold ? 16 : 13,
        fontWeight: bold ? 700 : 500,
        color: valueColor ?? (bold ? "var(--color-text)" : "var(--color-muted-2)"),
        ...valueStyle,
      }}>
        {fmt(value)}
      </span>
    </div>
  );
}

// ─── CartItemRow ──────────────────────────────────────────────────────────────
function CartItemRow({
  item, onVoid,
}: {
  item: ReturnType<typeof useOrder>["data"] extends { items: Array<infer T> } ? T : never;
  onVoid?: () => void;
}) {
  const [hovering, setHovering] = useState(false);

  return (
    <div
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        padding: "10px 10px",
        borderRadius: "var(--radius-sm)",
        background: hovering ? "var(--color-brand-3)" : "transparent",
        marginBottom: 2,
        transition: "background 0.1s",
      }}
    >
      {/* Qty badge */}
      <div style={{
        width: 24, height: 24,
        borderRadius: 6,
        background: "var(--color-brand)",
        border: "1px solid var(--color-border)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontFamily: "var(--font-mono)",
        fontSize: 11, fontWeight: 500,
        color: "var(--color-text)",
        flexShrink: 0,
        marginTop: 1,
      }}>
        {item.quantity}
      </div>

      {/* Name + modifiers */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontFamily: "var(--font-body)",
          fontSize: 13, fontWeight: 500,
          color: "var(--color-text)",
          lineHeight: 1.4,
        }}>
          {item.menu_item_name}
          {item.variant_name && (
            <span style={{
              fontFamily: "var(--font-mono)",
              fontSize: 10, color: "var(--color-muted)",
              marginLeft: 6,
            }}>
              ({item.variant_name})
            </span>
          )}
        </div>
        {item.modifiers.length > 0 && (
          <div style={{
            fontFamily: "var(--font-mono)", fontSize: 10,
            color: "var(--color-muted)", marginTop: 2,
          }}>
            {item.modifiers.map((m) => m.option_name).join(", ")}
          </div>
        )}
        {item.note && (
          <div style={{
            fontFamily: "var(--font-mono)", fontSize: 10,
            color: "var(--color-warning)", marginTop: 2,
          }}>
            📝 {item.note}
          </div>
        )}
        {item.sent_to_kitchen && (
          <div style={{
            fontFamily: "var(--font-mono)", fontSize: 10,
            color: "var(--color-success)", marginTop: 2,
          }}>
            ✓ Sent
          </div>
        )}
      </div>

      {/* Price */}
      <div style={{ textAlign: "right", flexShrink: 0 }}>
        <div style={{
          fontFamily: "var(--font-mono)",
          fontSize: 13, fontWeight: 500,
          color: "var(--color-text)",
        }}>
          {fmt(item.line_total)}
        </div>

        {/* Void button — shows on hover */}
        {onVoid && hovering && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onVoid();
            }}
            style={{
              marginTop: 4,
              background: "none",
              border: "none",
              color: "var(--color-danger)",
              cursor: "pointer",
              fontSize: 10,
              fontFamily: "var(--font-mono)",
              padding: "2px 4px",
              borderRadius: 4,
              display: "flex",
              alignItems: "center",
              gap: 3,
              marginLeft: "auto",
            }}
          >
            <X size={10} /> Void
          </button>
        )}
      </div>
    </div>
  );
}

// ─── ActionsPanel ─────────────────────────────────────────────────────────────
function ActionsPanel({
  order, hasUnsent, orderClosed,
  onSend, sending, onPay,
  canVoidOrder, canDiscount,
}: {
  order: ReturnType<typeof useOrder>["data"];
  hasUnsent: boolean;
  orderClosed: boolean;
  onSend: () => void;
  sending: boolean;
  onPay: () => void;
  canVoidOrder: boolean;
  canDiscount: boolean;
}) {
  const total = parseFloat(order?.total_amount ?? "0");

  return (
    <div style={{
      display: "flex", flexDirection: "column",
      height: "100%", padding: 14, gap: 10,
    }}>
      {/* Order info */}
      <div style={{
        padding: "12px 14px",
        background: "var(--color-brand-2)",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--color-border)",
      }}>
        <div style={{
          fontFamily: "var(--font-mono)",
          fontSize: 10, color: "var(--color-muted)",
          textTransform: "uppercase", letterSpacing: "0.1em",
          marginBottom: 4,
        }}>
          Order Total
        </div>
        <div style={{
          fontFamily: "var(--font-display)",
          fontSize: 28, fontWeight: 800,
          color: "var(--color-text)",
          letterSpacing: "-1px",
        }}>
          {fmt(order?.total_amount ?? "0.00")}
        </div>
      </div>

      <div style={{ flex: 1 }} />

      {/* Send to Kitchen */}
      <ActionBtn
        label={sending ? "Sending..." : "Send to Kitchen"}
        icon={<ChefHat size={16} />}
        onClick={onSend}
        disabled={!hasUnsent || orderClosed || sending}
        variant="secondary"
      />

      {/* Discount */}
      {canDiscount && (
        <ActionBtn
          label="Apply Discount"
          icon={<Percent size={16} />}
          onClick={() => {/* TODO: discount modal */}}
          disabled={orderClosed || total === 0}
          variant="ghost"
        />
      )}

      {/* Split Bill */}
      <ActionBtn
        label="Split Bill"
        icon={<SplitSquareVertical size={16} />}
        onClick={() => {/* TODO: split modal */}}
        disabled={orderClosed || total === 0}
        variant="ghost"
      />

      <div style={{ height: 1, background: "var(--color-border)" }} />

      {/* Pay */}
      <ActionBtn
        label="Pay"
        icon={<CreditCard size={16} />}
        onClick={onPay}
        disabled={orderClosed || total === 0}
        variant="primary"
        large
      />
    </div>
  );
}

function ActionBtn({
  label, icon, onClick, disabled, variant, large,
}: {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "ghost";
  large?: boolean;
}) {
  const bg =
    variant === "primary" ? "var(--color-accent)"
    : variant === "secondary" ? "var(--color-brand-2)"
    : "transparent";

  const border =
    variant === "ghost" ? "1px solid var(--color-border)"
    : variant === "secondary" ? "1px solid var(--color-border)"
    : "none";

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        width: "100%",
        height: large ? 52 : 44,
        background: disabled ? "var(--color-brand-2)" : bg,
        border,
        borderRadius: "var(--radius-md)",
        color: disabled
          ? "var(--color-muted)"
          : variant === "primary"
          ? "#fff"
          : "var(--color-text)",
        fontFamily: "var(--font-display)",
        fontSize: large ? 16 : 14,
        fontWeight: 700,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        transition: "all 0.15s",
        minHeight: "var(--touch-target)",
      }}
    >
      {icon} {label}
    </button>
  );
}

// ─── Station Picker Modal ─────────────────────────────────────────────────────
function StationPickerModal({
  stations, onSelect, onClose,
}: {
  stations: any[];
  onSelect: (stationId?: string) => void;
  onClose: () => void;
}) {
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
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
          fontSize: 17, fontWeight: 700,
          color: "var(--color-text)",
          margin: "0 0 16px",
        }}>
          Send to Station
        </h3>

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <StationBtn
            label="All Stations"
            color="#64748b"
            onClick={() => onSelect(undefined)}
          />
          {stations.map((s) => (
            <StationBtn
              key={s.id}
              label={s.name}
              color={s.color}
              onClick={() => onSelect(s.id)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function StationBtn({
  label, color, onClick,
}: {
  label: string; color: string; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", gap: 12,
        padding: "12px 14px",
        background: "var(--color-brand-3)",
        border: `1px solid ${color}40`,
        borderRadius: "var(--radius-md)",
        cursor: "pointer",
        textAlign: "left",
        width: "100%",
        minHeight: "var(--touch-target)",
      }}
    >
      <div style={{ width: 12, height: 12, borderRadius: "50%", background: color, flexShrink: 0 }} />
      <span style={{
        fontFamily: "var(--font-body)",
        fontSize: 14, fontWeight: 500,
        color: "var(--color-text)",
      }}>
        {label}
      </span>
    </button>
  );
}