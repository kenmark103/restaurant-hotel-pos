import { ReactNode } from "react";

interface PosLayoutProps {
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
  topBar?: ReactNode;
}

/**
 * Full-screen 3-panel POS layout:
 *  [topBar — full width]
 *  [left: menu/categories | center: cart | right: actions]
 */
export function PosLayout({ left, center, right, topBar }: PosLayoutProps) {
  return (
    <div style={{
      height: "100dvh",
      display: "flex",
      flexDirection: "column",
      background: "var(--color-brand)",
      overflow: "hidden",
    }}>
      {topBar && (
        <div style={{
          height: 52,
          background: "var(--color-brand-2)",
          borderBottom: "1px solid var(--color-border)",
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          paddingInline: 16,
          gap: 16,
        }}>
          {topBar}
        </div>
      )}

      <div style={{
        flex: 1,
        display: "grid",
        gridTemplateColumns: "1fr 380px 260px",
        overflow: "hidden",
        gap: 0,
      }}>
        {/* Left panel — menu browser */}
        <div style={{
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          borderRight: "1px solid var(--color-border)",
        }}>
          {left}
        </div>

        {/* Center panel — cart */}
        <div style={{
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          borderRight: "1px solid var(--color-border)",
          background: "var(--color-brand-2)",
        }}>
          {center}
        </div>

        {/* Right panel — actions */}
        <div style={{
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          background: "var(--color-brand-3)",
        }}>
          {right}
        </div>
      </div>
    </div>
  );
}

/**
 * KDS full-screen layout — no nav, just status bar + ticket grid
 */
export function KdsLayout({
  statusBar,
  children,
}: {
  statusBar: ReactNode;
  children: ReactNode;
}) {
  return (
    <div style={{
      height: "100dvh",
      display: "flex",
      flexDirection: "column",
      background: "var(--color-brand)",
      overflow: "hidden",
    }}>
      <div style={{
        height: 44,
        background: "var(--color-brand-2)",
        borderBottom: "1px solid var(--color-border)",
        display: "flex",
        alignItems: "center",
        paddingInline: 16,
        gap: 16,
        flexShrink: 0,
      }}>
        {statusBar}
      </div>
      <div style={{ flex: 1, overflow: "hidden" }}>
        {children}
      </div>
    </div>
  );
}