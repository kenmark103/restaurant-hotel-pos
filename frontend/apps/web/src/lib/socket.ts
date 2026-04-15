import { io, Socket } from "socket.io-client";
import { queryClient } from "./queryClient";

// ─── Event payload types ───────────────────────────────────────────────────
export interface WsTableStatusEvent {
  table_id: number;
  status: string;
  order_id?: number;
}

export interface WsOrderChangedEvent {
  order_id: number;
  type: "order_updated" | "order_closed" | "order_voided" | "item_added";
  branch_id: number;
}

export interface WsNewTicketEvent {
  ticket_id: number;
  station_id: string;
  order_id: number;
  branch_id: number;
}

export interface WsTicketStatusEvent {
  ticket_id: number;
  status: string;
  station_id: string;
}

export interface WsLowStockEvent {
  item_id: number;
  item_name: string;
  current_stock: number;
  threshold: number;
  branch_id: number;
}

// ─── Singleton socket ──────────────────────────────────────────────────────
let socket: Socket | null = null;

export function getSocket(): Socket | null {
  return socket;
}

export function connectSocket(accessToken: string, branchId: number): Socket {
  if (socket?.connected) return socket;

  const wsUrl =
    (import.meta as unknown as { env: Record<string, string> }).env
      ?.VITE_WS_URL ?? "http://localhost:8000";

  socket = io(wsUrl, {
    auth: { token: accessToken },
    transports: ["websocket"],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 10_000,
    reconnectionAttempts: 5,
  });

  socket.on("connect", () => {
    console.log("[WS] connected");
    // Join floor room — all POS users
    socket?.emit("join", `branch_${branchId}_floor`);
  });

  socket.on("disconnect", (reason) => {
    console.log("[WS] disconnected:", reason);
  });

  // ── Event handlers ──────────────────────────────────────────────────────
  socket.on("table_status", (data: WsTableStatusEvent) => {
    queryClient.invalidateQueries({ queryKey: ["tables"] });
    console.log("[WS] table_status", data);
  });

  socket.on("order_changed", (data: WsOrderChangedEvent) => {
    queryClient.invalidateQueries({
      queryKey: ["orders", data.branch_id],
    });
    queryClient.invalidateQueries({
      queryKey: ["order", data.order_id],
    });
  });

  socket.on("new_ticket", (data: WsNewTicketEvent) => {
    queryClient.invalidateQueries({ queryKey: ["kds-tickets"] });
    console.log("[WS] new_ticket", data);
  });

  socket.on("ticket_status", (data: WsTicketStatusEvent) => {
    queryClient.invalidateQueries({ queryKey: ["kds-tickets"] });
  });

  socket.on("low_stock_alert", (data: WsLowStockEvent) => {
    // Dispatch a custom DOM event — toast system listens
    window.dispatchEvent(
      new CustomEvent("pos:low-stock", { detail: data })
    );
  });

  return socket;
}

export function joinKitchenRoom(branchId: number, stationId: string): void {
  socket?.emit("join", `branch_${branchId}_kitchen_${stationId}`);
}

export function leaveKitchenRoom(branchId: number, stationId: string): void {
  socket?.emit("leave", `branch_${branchId}_kitchen_${stationId}`);
}

export function disconnectSocket(): void {
  socket?.disconnect();
  socket = null;
}