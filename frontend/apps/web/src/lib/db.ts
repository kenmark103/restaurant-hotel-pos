import Dexie, { type Table } from "dexie";

// ─── Table shapes ────────────────────────────────────────────────────────────
export interface OfflineAction {
  id?: number;
  clientId: string;
  method: "GET" | "POST" | "PATCH" | "DELETE";
  url: string;
  body?: unknown;
  timestamp: number;
  retries: number;
}

export interface CachedMenu {
  id?: number;
  branchId: number;
  data: unknown;
  cachedAt: number;
}

export interface CachedTables {
  id?: number;
  branchId: number;
  data: unknown;
  cachedAt: number;
}

export interface CachedSettings {
  id?: number;
  key: string;        // "venue" | "product_config"
  data: unknown;
  cachedAt: number;
}

export interface PendingReceipt {
  id?: number;
  orderId: number;
  printJobId: number;
  queuedAt: number;
}

// ─── Database ────────────────────────────────────────────────────────────────
class RestaurantDb extends Dexie {
  offline_actions!: Table<OfflineAction>;
  cached_menu!:     Table<CachedMenu>;
  cached_tables!:   Table<CachedTables>;
  cached_settings!: Table<CachedSettings>;
  pending_receipts!:Table<PendingReceipt>;

  constructor() {
    super("restaurantos");
    this.version(1).stores({
      offline_actions:  "++id, clientId, timestamp",
      cached_menu:      "++id, branchId, cachedAt",
      cached_tables:    "++id, branchId, cachedAt",
      cached_settings:  "++id, key, cachedAt",
      pending_receipts: "++id, orderId, queuedAt",
    });
  }
}

export const db = new RestaurantDb();

// ─── Cache helpers ────────────────────────────────────────────────────────────
const MENU_TTL    = 1000 * 60 * 10;  // 10 min
const TABLES_TTL  = 1000 * 60 * 5;   // 5 min
const SETTINGS_TTL= 1000 * 60 * 30;  // 30 min

export async function getCachedMenu(branchId: number): Promise<unknown | null> {
  const row = await db.cached_menu
    .where("branchId")
    .equals(branchId)
    .last();
  if (!row) return null;
  if (Date.now() - row.cachedAt > MENU_TTL) return null;
  return row.data;
}

export async function setCachedMenu(
  branchId: number,
  data: unknown
): Promise<void> {
  await db.cached_menu.where("branchId").equals(branchId).delete();
  await db.cached_menu.add({ branchId, data, cachedAt: Date.now() });
}

export async function getCachedTables(
  branchId: number
): Promise<unknown | null> {
  const row = await db.cached_tables
    .where("branchId")
    .equals(branchId)
    .last();
  if (!row) return null;
  if (Date.now() - row.cachedAt > TABLES_TTL) return null;
  return row.data;
}

export async function setCachedTables(
  branchId: number,
  data: unknown
): Promise<void> {
  await db.cached_tables.where("branchId").equals(branchId).delete();
  await db.cached_tables.add({ branchId, data, cachedAt: Date.now() });
}

export async function getCachedSettings(
  key: string
): Promise<unknown | null> {
  const row = await db.cached_settings.where("key").equals(key).last();
  if (!row) return null;
  if (Date.now() - row.cachedAt > SETTINGS_TTL) return null;
  return row.data;
}

export async function setCachedSettings(
  key: string,
  data: unknown
): Promise<void> {
  await db.cached_settings.where("key").equals(key).delete();
  await db.cached_settings.add({ key, data, cachedAt: Date.now() });
}