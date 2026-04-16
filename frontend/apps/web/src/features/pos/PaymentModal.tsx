import { useState, useEffect } from "react";
import { useCloseOrder } from "@/hooks/useApi";
import type { OrderRead, PaymentMethod } from "@restaurantos/api";
import { fmt } from "@/lib/cn";
import { X, CreditCard, Smartphone, Banknote, SplitSquareVertical, Check } from "lucide-react";

interface SplitEntry {
  method: PaymentMethod;
  amount: string;
}

const METHODS: { value: PaymentMethod; label: string; icon: React.ReactNode }[] = [
  { value: "cash",         label: "Cash",        icon: <Banknote size={18} /> },
  { value: "mobile_money", label: "M-Pesa",      icon: <Smartphone size={18} /> },
  { value: "card",         label: "Card",        icon: <CreditCard size={18} /> },
  { value: "complimentary",label: "Complimentary",icon: <Check size={18} /> },
];

export function PaymentModal({
  order,
  onClose,
  onSuccess,
}: {
  order: OrderRead;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const total = parseFloat(order.total_amount);
  const closeOrder = useCloseOrder(order.id);

  const [selectedMethod, setSelectedMethod] = useState<PaymentMethod>("cash");
  const [amountStr, setAmountStr] = useState(order.total_amount);
  const [isSplit, setIsSplit] = useState(false);
  const [splits, setSplits] = useState<SplitEntry[]>([
    { method: "cash", amount: "" },
    { method: "mobile_money", amount: "" },
  ]);
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);

  const amountPaid = parseFloat(amountStr) || 0;
  const changeDue  = Math.max(0, amountPaid - total);

  const splitsTotal = splits.reduce((s, e) => s + (parseFloat(e.amount) || 0), 0);
  const splitsRemaining = total - splitsTotal;

  const handleSinglePay = () => {
    setError(null);
    if (amountPaid < total) {
      setError(`Amount must be at least ${fmt(total)}`);
      return;
    }
    closeOrder.mutate(
      {
        payment_method: selectedMethod,
        amount_paid: amountPaid,
      },
      { onSuccess }
    );
  };

  const handleSplitPay = () => {
    setError(null);
    if (Math.abs(splitsTotal - total) > 0.01) {
      setError(`Split amounts must equal ${fmt(total)}`);
      return;
    }
    closeOrder.mutate(
      {
        payment_method: splits[0]?.method ?? "cash",
        amount_paid: total,
        split_payments: splits
          .filter((s) => parseFloat(s.amount) > 0)
          .map((s) => ({ method: s.method, amount: parseFloat(s.amount) })),
      },
      { onSuccess }
    );
  };

  // Numeric keypad digit press
  const handleKeypad = (digit: string) => {
    setAmountStr((prev) => {
      if (digit === "." && prev.includes(".")) return prev;
      if (digit === "C") return "0";
      const next = prev === "0" && digit !== "."
        ? digit
        : prev + digit;
      return next;
    });
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0,
        background: "rgba(0,0,0,0.7)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 100,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="animate-slide-up card"
        style={{
          width: "100%", maxWidth: 480,
          maxHeight: "90dvh",
          overflow: "auto",
          padding: 24,
        }}
      >
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 20,
        }}>
          <div>
            <h2 style={{
              fontFamily: "var(--font-display)",
              fontSize: 20, fontWeight: 700,
              color: "var(--color-text)",
              margin: 0,
            }}>
              Payment
            </h2>
            <div style={{
              fontFamily: "var(--font-mono)",
              fontSize: 12, color: "var(--color-muted)",
              marginTop: 2,
            }}>
              Order #{order.id}
              {order.table && ` · Table ${order.table.table_number}`}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none", border: "none",
              color: "var(--color-muted)", cursor: "pointer", lineHeight: 0,
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Total */}
        <div style={{
          textAlign: "center",
          padding: "16px 0",
          marginBottom: 20,
          borderBottom: "1px solid var(--color-border)",
        }}>
          <div style={{
            fontFamily: "var(--font-mono)",
            fontSize: 11, color: "var(--color-muted)",
            textTransform: "uppercase", letterSpacing: "0.1em",
          }}>
            Amount Due
          </div>
          <div style={{
            fontFamily: "var(--font-display)",
            fontSize: 40, fontWeight: 800,
            color: "var(--color-text)",
            letterSpacing: "-2px",
            lineHeight: 1.1,
          }}>
            {fmt(order.total_amount)}
          </div>
        </div>

        {/* Split toggle */}
        <button
          onClick={() => setIsSplit((s) => !s)}
          style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "8px 14px",
            background: isSplit ? "rgba(59,130,246,0.15)" : "var(--color-brand-3)",
            border: `1px solid ${isSplit ? "var(--color-accent)" : "var(--color-border)"}`,
            borderRadius: "var(--radius-md)",
            color: isSplit ? "var(--color-accent-2)" : "var(--color-muted)",
            fontFamily: "var(--font-mono)",
            fontSize: 11, cursor: "pointer",
            marginBottom: 16,
          }}
        >
          <SplitSquareVertical size={13} />
          {isSplit ? "Single payment" : "Split payment"}
        </button>

        {!isSplit ? (
          /* ── Single tender ──────────────────────────────────────────── */
          <>
            {/* Method selector */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 8, marginBottom: 20,
            }}>
              {METHODS.map((m) => (
                <button
                  key={m.value}
                  onClick={() => setSelectedMethod(m.value)}
                  style={{
                    padding: "12px 8px",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid",
                    borderColor: selectedMethod === m.value
                      ? "var(--color-accent)"
                      : "var(--color-border)",
                    background: selectedMethod === m.value
                      ? "rgba(59,130,246,0.15)"
                      : "var(--color-brand-3)",
                    color: selectedMethod === m.value
                      ? "var(--color-accent-2)"
                      : "var(--color-muted)",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 6,
                    fontFamily: "var(--font-mono)",
                    fontSize: 10,
                    minHeight: "var(--touch-target)",
                    transition: "all 0.15s",
                  }}
                >
                  {m.icon}
                  {m.label}
                </button>
              ))}
            </div>

            {/* Amount tendered */}
            {selectedMethod === "cash" && (
              <>
                <div style={{
                  marginBottom: 8,
                  padding: "12px 16px",
                  background: "var(--color-brand)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}>
                  <span style={{
                    fontFamily: "var(--font-mono)", fontSize: 11,
                    color: "var(--color-muted)",
                    textTransform: "uppercase",
                  }}>
                    Tendered
                  </span>
                  <span style={{
                    fontFamily: "var(--font-display)",
                    fontSize: 22, fontWeight: 700,
                    color: "var(--color-text)",
                    letterSpacing: "-0.5px",
                  }}>
                    {fmt(amountStr)}
                  </span>
                </div>

                {changeDue > 0 && (
                  <div style={{
                    marginBottom: 8,
                    padding: "10px 16px",
                    background: "rgba(16,185,129,0.1)",
                    border: "1px solid rgba(16,185,129,0.3)",
                    borderRadius: "var(--radius-md)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}>
                    <span style={{
                      fontFamily: "var(--font-mono)", fontSize: 11,
                      color: "var(--color-success)",
                    }}>
                      Change Due
                    </span>
                    <span style={{
                      fontFamily: "var(--font-display)",
                      fontSize: 20, fontWeight: 700,
                      color: "var(--color-success)",
                    }}>
                      {fmt(changeDue)}
                    </span>
                  </div>
                )}

                {/* Numeric keypad */}
                <div style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: 8, marginBottom: 16,
                }}>
                  {["1","2","3","4","5","6","7","8","9","C","0","."].map((d) => (
                    <button
                      key={d}
                      onClick={() => handleKeypad(d)}
                      style={{
                        height: 48,
                        borderRadius: "var(--radius-sm)",
                        background: d === "C"
                          ? "rgba(239,68,68,0.15)"
                          : "var(--color-brand-3)",
                        border: "1px solid var(--color-border)",
                        color: d === "C"
                          ? "var(--color-danger)"
                          : "var(--color-text)",
                        fontFamily: "var(--font-display)",
                        fontSize: 18, fontWeight: 600,
                        cursor: "pointer",
                        minHeight: "var(--touch-target)",
                      }}
                    >
                      {d}
                    </button>
                  ))}
                </div>

                {/* Quick amounts */}
                <div style={{
                  display: "flex", gap: 8, marginBottom: 16,
                }}>
                  {[total, Math.ceil(total / 100) * 100, Math.ceil(total / 500) * 500].map(
                    (v, i) => (
                      <button
                        key={i}
                        onClick={() => setAmountStr(v.toFixed(2))}
                        style={{
                          flex: 1, padding: "8px 4px",
                          background: "var(--color-brand-3)",
                          border: "1px solid var(--color-border)",
                          borderRadius: "var(--radius-sm)",
                          color: "var(--color-muted-2)",
                          fontFamily: "var(--font-mono)",
                          fontSize: 12, cursor: "pointer",
                          minHeight: "var(--touch-target)",
                        }}
                      >
                        {fmt(v)}
                      </button>
                    )
                  )}
                </div>
              </>
            )}

            {/* M-Pesa phone input */}
            {selectedMethod === "mobile_money" && (
              <div style={{ marginBottom: 16 }}>
                <label style={{
                  display: "block", fontFamily: "var(--font-mono)",
                  fontSize: 11, color: "var(--color-muted)",
                  textTransform: "uppercase", letterSpacing: "0.1em",
                  marginBottom: 8,
                }}>
                  Customer Phone
                </label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="07XX XXX XXX"
                  style={{
                    width: "100%",
                    padding: "12px 14px",
                    background: "var(--color-brand)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-md)",
                    color: "var(--color-text)",
                    fontFamily: "var(--font-mono)",
                    fontSize: 15, outline: "none",
                  }}
                />
                <p style={{
                  fontFamily: "var(--font-mono)", fontSize: 11,
                  color: "var(--color-muted)", marginTop: 8,
                }}>
                  Customer will receive STK push prompt
                </p>
              </div>
            )}

            {error && (
              <p style={{
                fontFamily: "var(--font-mono)", fontSize: 12,
                color: "var(--color-danger)", marginBottom: 12,
              }}>
                {error}
              </p>
            )}

            <button
              onClick={handleSinglePay}
              disabled={closeOrder.isPending}
              style={{
                width: "100%", height: 52,
                background: "var(--color-accent)",
                border: "none",
                borderRadius: "var(--radius-md)",
                color: "#fff",
                fontFamily: "var(--font-display)",
                fontSize: 17, fontWeight: 700,
                cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center",
                gap: 8,
                opacity: closeOrder.isPending ? 0.7 : 1,
                transition: "opacity 0.15s",
              }}
            >
              {closeOrder.isPending
                ? "Processing..."
                : `Confirm ${METHODS.find((m) => m.value === selectedMethod)?.label}`
              }
            </button>
          </>
        ) : (
          /* ── Split tender ───────────────────────────────────────────── */
          <>
            {splits.map((s, i) => (
              <div key={i} style={{
                display: "flex", gap: 8,
                marginBottom: 10,
                alignItems: "center",
              }}>
                <select
                  value={s.method}
                  onChange={(e) => {
                    const copy = [...splits];
                    copy[i] = { ...s, method: e.target.value as PaymentMethod };
                    setSplits(copy);
                  }}
                  style={{
                    padding: "10px 12px",
                    background: "var(--color-brand-3)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-md)",
                    color: "var(--color-text)",
                    fontFamily: "var(--font-mono)", fontSize: 12,
                    cursor: "pointer",
                  }}
                >
                  {METHODS.map((m) => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </select>
                <input
                  type="number"
                  placeholder="0.00"
                  value={s.amount}
                  onChange={(e) => {
                    const copy = [...splits];
                    copy[i] = { ...s, amount: e.target.value };
                    setSplits(copy);
                  }}
                  style={{
                    flex: 1, padding: "10px 12px",
                    background: "var(--color-brand)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-md)",
                    color: "var(--color-text)",
                    fontFamily: "var(--font-mono)", fontSize: 14,
                    outline: "none",
                    textAlign: "right",
                  }}
                />
              </div>
            ))}

            {/* Remaining */}
            <div style={{
              display: "flex", justifyContent: "space-between",
              padding: "10px 0", marginBottom: 12,
              borderTop: "1px solid var(--color-border)",
            }}>
              <span style={{
                fontFamily: "var(--font-mono)", fontSize: 11,
                color: splitsRemaining > 0.01 ? "var(--color-warning)" : "var(--color-success)",
              }}>
                {splitsRemaining > 0.01
                  ? `Remaining: ${fmt(splitsRemaining)}`
                  : "✓ Fully covered"
                }
              </span>
            </div>

            {error && (
              <p style={{
                fontFamily: "var(--font-mono)", fontSize: 12,
                color: "var(--color-danger)", marginBottom: 12,
              }}>
                {error}
              </p>
            )}

            <button
              onClick={handleSplitPay}
              disabled={closeOrder.isPending || splitsRemaining > 0.01}
              style={{
                width: "100%", height: 52,
                background: "var(--color-accent)",
                border: "none",
                borderRadius: "var(--radius-md)",
                color: "#fff",
                fontFamily: "var(--font-display)",
                fontSize: 17, fontWeight: 700,
                cursor: "pointer",
                opacity: (closeOrder.isPending || splitsRemaining > 0.01) ? 0.5 : 1,
              }}
            >
              {closeOrder.isPending ? "Processing..." : "Confirm Split Payment"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}