import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation } from "@tanstack/react-query";
import { authApi, settingsApi, parseApiError } from "@restaurantos/api";
import { useSessionStore } from "@restaurantos/stores";
import { cn } from "@/lib/cn";
import { Delete, ChevronRight, Wifi, WifiOff } from "lucide-react";

// ─── Branch type ─────────────────────────────────────────────────────────────
interface Branch {
  id: number;
  name: string;
}

const LOCK_DURATION_MS = 5 * 60 * 1000; // 5 minutes
const MAX_ATTEMPTS = 5;
const PIN_LENGTH = 5;

export default function PinPadScreen() {
  const navigate = useNavigate();
  const login = useSessionStore((s) => s.login);

  // ── State ─────────────────────────────────────────────────────────────────
  const [pin, setPin] = useState("");
  const [selectedBranchId, setSelectedBranchId] = useState<number | null>(null);
  const [attempts, setAttempts] = useState(0);
  const [lockedUntil, setLockedUntil] = useState<number | null>(null);
  const [lockRemaining, setLockRemaining] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [shake, setShake] = useState(false);
  const pinInputRef = useRef<HTMLInputElement>(null);

  // ── Data ──────────────────────────────────────────────────────────────────
  const { data: publicSettings } = useQuery({
    queryKey: ["public-settings"],
    queryFn: () => settingsApi.getPublicSettings(),
    staleTime: Infinity,
  });

  const { data: branches } = useQuery({
    queryKey: ["branches-public"],
    queryFn: () => settingsApi.listBranches() as Promise<Branch[]>,
    staleTime: 1000 * 60 * 10,
  });

  // ── Lockout timer ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!lockedUntil) return;
    const interval = setInterval(() => {
      const remaining = Math.ceil((lockedUntil - Date.now()) / 1000);
      if (remaining <= 0) {
        setLockedUntil(null);
        setAttempts(0);
        setLockRemaining(0);
        clearInterval(interval);
      } else {
        setLockRemaining(remaining);
      }
    }, 500);
    return () => clearInterval(interval);
  }, [lockedUntil]);

  // ── Auto-select first branch ──────────────────────────────────────────────
  useEffect(() => {
    if (branches && branches.length === 1 && !selectedBranchId) {
      setSelectedBranchId(branches[0]?.id ?? null);
    }
  }, [branches, selectedBranchId]);

  // ── PIN login mutation ────────────────────────────────────────────────────
  const mutation = useMutation({
    mutationFn: authApi.pinLogin,
    onSuccess: (data) => {
      login(data.access_token, data.user);
      const role = data.user.role;
      if (role === "kitchen" || role === "kitchen_manager") {
        navigate({ to: "/kitchen" });
      } else {
        navigate({ to: "/pos" });
      }
    },
    onError: (err) => {
      const { status, message } = parseApiError(err);
      const newAttempts = attempts + 1;
      setAttempts(newAttempts);

      if (newAttempts >= MAX_ATTEMPTS || status === 423) {
        setLockedUntil(Date.now() + LOCK_DURATION_MS);
        setError("Too many failed attempts. PIN locked for 5 minutes.");
      } else {
        const remaining = MAX_ATTEMPTS - newAttempts;
        setError(
          status === 401
            ? `Incorrect PIN. ${remaining} attempt${remaining !== 1 ? "s" : ""} remaining.`
            : message
        );
      }

      // Shake + clear PIN
      setShake(true);
      setTimeout(() => {
        setShake(false);
        setPin("");
      }, 500);
    },
  });

  // ── Handlers ──────────────────────────────────────────────────────────────
  const isLocked = !!lockedUntil;
  const canSubmit =
    !isLocked && !!selectedBranchId && pin.length === PIN_LENGTH;

  const handleDigit = useCallback(
    (digit: string) => {
      if (isLocked || mutation.isPending) return;
      setError(null);
      setPin((p) => {
        const next = p + digit;
        if (next.length === PIN_LENGTH) {
          // Auto-submit when PIN is complete
          if (selectedBranchId) {
            setTimeout(() => {
              mutation.mutate({
                branch_id: selectedBranchId,
                pin: next,
              });
            }, 80); // tiny delay for UX feedback
          }
        }
        return next.slice(0, PIN_LENGTH);
      });
    },
    [isLocked, mutation, selectedBranchId]
  );

  const handleBackspace = useCallback(() => {
    if (isLocked || mutation.isPending) return;
    setError(null);
    setPin((p) => p.slice(0, -1));
  }, [isLocked, mutation.isPending]);

  // Keyboard support
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key >= "0" && e.key <= "9") handleDigit(e.key);
      else if (e.key === "Backspace") handleBackspace();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleDigit, handleBackspace]);

  // ── Render ────────────────────────────────────────────────────────────────
  const venueName =
    (publicSettings as { venue_name?: string } | null)?.venue_name ??
    "RestaurantOS";

  return (
    <div className="pin-screen" style={{
      minHeight: "100dvh",
      background: "var(--color-brand)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      padding: "24px",
      position: "relative",
      overflow: "hidden",
    }}>

      {/* Background grid texture */}
      <div style={{
        position: "absolute", inset: 0, opacity: 0.03,
        backgroundImage: `
          linear-gradient(rgba(59,130,246,0.5) 1px, transparent 1px),
          linear-gradient(90deg, rgba(59,130,246,0.5) 1px, transparent 1px)
        `,
        backgroundSize: "40px 40px",
        pointerEvents: "none",
      }} />

      {/* Glow orb */}
      <div style={{
        position: "absolute",
        top: "20%", left: "50%",
        transform: "translateX(-50%)",
        width: 400, height: 400,
        background: "radial-gradient(circle, rgba(59,130,246,0.12) 0%, transparent 70%)",
        pointerEvents: "none",
        filter: "blur(20px)",
      }} />

      {/* Card */}
      <div className="animate-fade-in" style={{
        width: "100%", maxWidth: 400,
        position: "relative", zIndex: 1,
      }}>

        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 52, height: 52,
            background: "var(--color-brand-3)",
            border: "1px solid var(--color-border)",
            borderRadius: 14,
            marginBottom: 16,
          }}>
            <span style={{ fontSize: 24 }}>🧾</span>
          </div>
          <h1 style={{
            fontFamily: "var(--font-display)",
            fontSize: 26, fontWeight: 700,
            color: "var(--color-text)",
            margin: 0, letterSpacing: "-0.5px",
          }}>
            {venueName}
          </h1>
          <p style={{
            fontFamily: "var(--font-mono)",
            fontSize: 12,
            color: "var(--color-muted)",
            margin: "6px 0 0",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}>
            Staff Login
          </p>
        </div>

        {/* Branch selector */}
        {branches && branches.length > 1 && (
          <div style={{ marginBottom: 20 }}>
            <label style={{
              display: "block",
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: "var(--color-muted)",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              marginBottom: 8,
            }}>
              Branch
            </label>
            <select
              value={selectedBranchId ?? ""}
              onChange={(e) =>
                setSelectedBranchId(
                  e.target.value ? Number(e.target.value) : null
                )
              }
              style={{
                width: "100%",
                padding: "12px 16px",
                background: "var(--color-brand-2)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                color: "var(--color-text)",
                fontFamily: "var(--font-body)",
                fontSize: 15,
                cursor: "pointer",
                appearance: "none",
              }}
            >
              <option value="">Select a branch</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* PIN dots */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 14,
          marginBottom: 24,
          height: 56,
        }}>
          {Array.from({ length: PIN_LENGTH }).map((_, i) => {
            const filled = i < pin.length;
            const isActive = i === pin.length && !isLocked;
            return (
              <div
                key={i}
                className={shake ? "pin-shake" : ""}
                style={{
                  width: filled ? 18 : 14,
                  height: filled ? 18 : 14,
                  borderRadius: "50%",
                  background: filled
                    ? isLocked
                      ? "var(--color-danger)"
                      : "var(--color-accent)"
                    : "transparent",
                  border: `2px solid ${
                    filled
                      ? isLocked
                        ? "var(--color-danger)"
                        : "var(--color-accent)"
                      : isActive
                      ? "var(--color-accent)"
                      : "var(--color-border)"
                  }`,
                  transition: "all 0.15s ease",
                  boxShadow: filled && !isLocked
                    ? "0 0 8px rgba(59,130,246,0.5)"
                    : "none",
                }}
              />
            );
          })}
        </div>

        {/* Error / lock message */}
        <div style={{
          minHeight: 36,
          textAlign: "center",
          marginBottom: 20,
        }}>
          {isLocked ? (
            <div style={{
              padding: "10px 16px",
              background: "rgba(239,68,68,0.1)",
              border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: "var(--radius-md)",
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              color: "var(--color-danger)",
            }}>
              🔒 Locked — try again in {Math.floor(lockRemaining / 60)}:
              {String(lockRemaining % 60).padStart(2, "0")}
            </div>
          ) : error ? (
            <p style={{
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              color: "var(--color-danger)",
              margin: 0,
              animation: "fadeIn 0.2s ease",
            }}>
              {error}
            </p>
          ) : null}
        </div>

        {/* Numpad */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 10,
        }}>
          {["1","2","3","4","5","6","7","8","9"].map((d) => (
            <NumKey
              key={d}
              label={d}
              onPress={() => handleDigit(d)}
              disabled={isLocked || mutation.isPending || pin.length >= PIN_LENGTH}
            />
          ))}
          {/* Bottom row: empty, 0, backspace */}
          <div />
          <NumKey
            label="0"
            onPress={() => handleDigit("0")}
            disabled={isLocked || mutation.isPending || pin.length >= PIN_LENGTH}
          />
          <NumKey
            label={<Delete size={18} />}
            onPress={handleBackspace}
            disabled={isLocked || mutation.isPending || pin.length === 0}
            variant="ghost"
          />
        </div>

        {/* Loading indicator */}
        {mutation.isPending && (
          <div style={{
            textAlign: "center",
            marginTop: 20,
            fontFamily: "var(--font-mono)",
            fontSize: 12,
            color: "var(--color-muted)",
          }}>
            <span style={{ animation: "blink 1s ease infinite" }}>
              Authenticating...
            </span>
          </div>
        )}

        {/* Email login fallback */}
        <div style={{ textAlign: "center", marginTop: 28 }}>
          <a
            href="/auth/login"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: "var(--color-muted)",
              textDecoration: "none",
              letterSpacing: "0.05em",
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              padding: "8px 12px",
              borderRadius: "var(--radius-sm)",
              transition: "color 0.15s",
            }}
            onMouseEnter={(e) =>
              ((e.target as HTMLElement).style.color = "var(--color-muted-2)")
            }
            onMouseLeave={(e) =>
              ((e.target as HTMLElement).style.color = "var(--color-muted)")
            }
          >
            Email login <ChevronRight size={12} />
          </a>
        </div>
      </div>

      {/* Connection indicator */}
      <OnlineIndicator />

      {/* Keyframe for shake */}
      <style>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          15%  { transform: translateX(-8px); }
          30%  { transform: translateX(8px); }
          45%  { transform: translateX(-6px); }
          60%  { transform: translateX(6px); }
          75%  { transform: translateX(-3px); }
          90%  { transform: translateX(3px); }
        }
        .pin-shake { animation: shake 0.4s ease; }
      `}</style>
    </div>
  );
}

// ─── NumKey component ─────────────────────────────────────────────────────────
interface NumKeyProps {
  label: React.ReactNode;
  onPress: () => void;
  disabled?: boolean;
  variant?: "default" | "ghost";
}

function NumKey({ label, onPress, disabled, variant = "default" }: NumKeyProps) {
  const [pressed, setPressed] = useState(false);

  return (
    <button
      type="button"
      onPointerDown={() => !disabled && setPressed(true)}
      onPointerUp={() => { setPressed(false); if (!disabled) onPress(); }}
      onPointerLeave={() => setPressed(false)}
      disabled={disabled}
      style={{
        height: 64,
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--color-border)",
        background: pressed
          ? "var(--color-brand-3)"
          : variant === "ghost"
          ? "transparent"
          : "var(--color-brand-2)",
        color: disabled ? "var(--color-muted)" : "var(--color-text)",
        fontFamily: "var(--font-display)",
        fontSize: variant === "ghost" ? 16 : 22,
        fontWeight: 600,
        cursor: disabled ? "not-allowed" : "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transition: "all 0.1s ease",
        transform: pressed ? "scale(0.95)" : "scale(1)",
        boxShadow: pressed
          ? "none"
          : "0 1px 3px rgba(0,0,0,0.3)",
        userSelect: "none",
        WebkitTapHighlightColor: "transparent",
        outline: "none",
        minWidth: "var(--touch-target)",
        minHeight: "var(--touch-target)",
      }}
    >
      {label}
    </button>
  );
}

// ─── Online indicator ─────────────────────────────────────────────────────────
function OnlineIndicator() {
  const [online, setOnline] = useState(navigator.onLine);

  useEffect(() => {
    const on  = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online",  on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online",  on);
      window.removeEventListener("offline", off);
    };
  }, []);

  return (
    <div style={{
      position: "absolute",
      bottom: 20, right: 20,
      display: "flex",
      alignItems: "center",
      gap: 6,
      fontFamily: "var(--font-mono)",
      fontSize: 11,
      color: online ? "var(--color-success)" : "var(--color-danger)",
    }}>
      {online
        ? <><Wifi size={13} /> Online</>
        : <><WifiOff size={13} /> Offline</>
      }
    </div>
  );
}