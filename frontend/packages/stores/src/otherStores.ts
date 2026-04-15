import { create } from "zustand";

// ─── UI Store ─────────────────────────────────────────────────────────────────
interface UiState {
  activeTableId: number | null;
  activeStationId: string | null;
  sidebarOpen: boolean;
  theme: "light" | "dark";
  pinModalOpen: boolean;
  overrideAction: string | null;

  setActiveTable: (id: number | null) => void;
  setActiveStation: (id: string | null) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setTheme: (t: "light" | "dark") => void;
  openPinModal: (action: string) => void;
  closePinModal: () => void;
}

export const useUiStore = create<UiState>((set) => ({
  activeTableId: null,
  activeStationId: null,
  sidebarOpen: false,
  theme: "dark",
  pinModalOpen: false,
  overrideAction: null,

  setActiveTable: (id) => set({ activeTableId: id }),
  setActiveStation: (id) => set({ activeStationId: id }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setTheme: (theme) => set({ theme }),
  openPinModal: (action) => set({ pinModalOpen: true, overrideAction: action }),
  closePinModal: () => set({ pinModalOpen: false, overrideAction: null }),
}));

// ─── Offline Store ────────────────────────────────────────────────────────────
interface QueuedAction {
  id: string;
  method: "GET" | "POST" | "PATCH" | "DELETE";
  url: string;
  body?: unknown;
  timestamp: number;
}

interface OfflineState {
  isOnline: boolean;
  queuedActions: QueuedAction[];
  lastSyncAt: number | null;

  setOnline: (online: boolean) => void;
  enqueue: (action: Omit<QueuedAction, "id" | "timestamp">) => void;
  dequeue: (id: string) => void;
  clearQueue: () => void;
  setLastSync: (ts: number) => void;
}

export const useOfflineStore = create<OfflineState>((set) => ({
  isOnline: navigator.onLine,
  queuedActions: [],
  lastSyncAt: null,

  setOnline: (isOnline) => set({ isOnline }),

  enqueue: (action) =>
    set((s) => ({
      queuedActions: [
        ...s.queuedActions,
        {
          ...action,
          id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
          timestamp: Date.now(),
        },
      ],
    })),

  dequeue: (id) =>
    set((s) => ({
      queuedActions: s.queuedActions.filter((a) => a.id !== id),
    })),

  clearQueue: () => set({ queuedActions: [] }),
  setLastSync: (ts) => set({ lastSyncAt: ts }),
}));

// ─── Cash Session Store ───────────────────────────────────────────────────────
interface CashSessionState {
  sessionId: number | null;
  openingFloat: string | null;
  status: "open" | "closed" | null;

  openSession: (id: number, float: string) => void;
  closeSession: () => void;
  setSession: (data: {
    sessionId: number;
    openingFloat: string;
    status: "open" | "closed";
  }) => void;
}

export const useCashStore = create<CashSessionState>((set) => ({
  sessionId: null,
  openingFloat: null,
  status: null,

  openSession: (sessionId, openingFloat) =>
    set({ sessionId, openingFloat, status: "open" }),

  closeSession: () => set({ status: "closed" }),

  setSession: ({ sessionId, openingFloat, status }) =>
    set({ sessionId, openingFloat, status }),
}));

// ─── WebSocket Store ──────────────────────────────────────────────────────────
interface WsState {
  connected: boolean;
  lastEventType: string | null;
  rooms: string[];

  setConnected: (connected: boolean) => void;
  setLastEvent: (type: string) => void;
  joinRoom: (room: string) => void;
  leaveRoom: (room: string) => void;
  clearRooms: () => void;
}

export const useWsStore = create<WsState>((set) => ({
  connected: false,
  lastEventType: null,
  rooms: [],

  setConnected: (connected) => set({ connected }),
  setLastEvent: (type) => set({ lastEventType: type }),
  joinRoom: (room) =>
    set((s) => ({
      rooms: s.rooms.includes(room) ? s.rooms : [...s.rooms, room],
    })),
  leaveRoom: (room) =>
    set((s) => ({ rooms: s.rooms.filter((r) => r !== room) })),
  clearRooms: () => set({ rooms: [] }),
}));