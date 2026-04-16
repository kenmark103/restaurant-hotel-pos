// ─── Kitchen ─────────────────────────────────────────────────────────────────
import { apiClient } from "../src/client";

export const kitchenApi = {
  listTickets: (params: {
    branch_id: number;
    station_id?: string;
    status?: string;
  }) =>
    apiClient
      .get<unknown[]>("/api/v1/kitchen/tickets", { params })
      .then((r) => r.data),

  updateTicketStatus: (
    ticketId: number,
    body: { status: string }
  ) =>
    apiClient
      .patch<unknown>(
        `/api/v1/kitchen/tickets/${ticketId}/status`,
        body
      )
      .then((r) => r.data),

  rushTicket: (ticketId: number) =>
    apiClient
      .post<unknown>(`/api/v1/kitchen/tickets/${ticketId}/rush`, {})
      .then((r) => r.data),

  listStations: (params?: { branch_id?: number }) =>
    apiClient
      .get<unknown[]>("/api/v1/kitchen/stations", { params })
      .then((r) => r.data),
};

// ─── Inventory ────────────────────────────────────────────────────────────────
export const inventoryApi = {
  listStockLevels: (params: { branch_id: number; category_id?: number }) =>
    apiClient
      .get<unknown[]>("/api/v1/inventory/stock", { params })
      .then((r) => r.data),

  adjustStock: (body: unknown) =>
    apiClient
      .post<unknown>("/api/v1/inventory/adjustments", body)
      .then((r) => r.data),

  logWaste: (body: unknown) =>
    apiClient
      .post<unknown>("/api/v1/inventory/waste", body)
      .then((r) => r.data),

  listMovements: (params: {
    branch_id: number;
    item_id?: number;
    date_from?: string;
    date_to?: string;
    type?: string;
  }) =>
    apiClient
      .get<unknown[]>("/api/v1/inventory/movements", { params })
      .then((r) => r.data),
};

// ─── Reports ──────────────────────────────────────────────────────────────────
export const reportsApi = {
  getDaily: (params: { branch_id: number; date?: string }) =>
    apiClient
      .get<unknown>("/api/v1/reports/daily", { params })
      .then((r) => r.data),

  getTopItems: (params: {
    branch_id: number;
    date_from?: string;
    date_to?: string;
    limit?: number;
  }) =>
    apiClient
      .get<unknown[]>("/api/v1/reports/items", { params })
      .then((r) => r.data),

  getStaffPerformance: (params: { branch_id: number; date?: string }) =>
    apiClient
      .get<unknown>("/api/v1/reports/staff", { params })
      .then((r) => r.data),

  getInventoryValuation: (params: { branch_id: number }) =>
    apiClient
      .get<unknown>("/api/v1/reports/inventory", { params })
      .then((r) => r.data),

  exportCsv: (params: { branch_id: number; date?: string }) =>
    apiClient
      .get<Blob>("/api/v1/reports/export/csv", {
        params,
        responseType: "blob",
      })
      .then((r) => r.data),
};

// ─── Settings ─────────────────────────────────────────────────────────────────
export const settingsApi = {
  getPublicSettings: () =>
    apiClient
      .get<unknown>("/api/v1/settings/public")
      .then((r) => r.data),

  getVenue: () =>
    apiClient.get<unknown>("/api/v1/settings/venue").then((r) => r.data),

  updateVenue: (body: unknown) =>
    apiClient
      .patch<unknown>("/api/v1/settings/venue", body)
      .then((r) => r.data),

  listBranches: () =>
    apiClient
      .get<unknown[]>("/api/v1/settings/branches")
      .then((r) => r.data),

  createBranch: (body: unknown) =>
    apiClient
      .post<unknown>("/api/v1/settings/branches", body)
      .then((r) => r.data),

  updateBranch: (branchId: number, body: unknown) =>
    apiClient
      .patch<unknown>(`/api/v1/settings/branches/${branchId}`, body)
      .then((r) => r.data),

  getProductConfiguration: () =>
    apiClient
      .get<import("../src/schema").components["schemas"]["ProductConfigurationResponse"]>(
        "/api/v1/settings/product/configuration"
      )
      .then((r) => r.data),

  listTaxTemplates: () =>
    apiClient
      .get<unknown[]>("/api/v1/settings/product/taxes")
      .then((r) => r.data),

  createTaxTemplate: (body: unknown) =>
    apiClient
      .post<unknown>("/api/v1/settings/product/taxes", body)
      .then((r) => r.data),

  listUnits: () =>
    apiClient
      .get<unknown[]>("/api/v1/settings/product/units")
      .then((r) => r.data),

  createUnit: (body: unknown) =>
    apiClient
      .post<unknown>("/api/v1/settings/product/units", body)
      .then((r) => r.data),

  listKitchenStations: () =>
    apiClient
      .get<unknown[]>("/api/v1/settings/product/stations")
      .then((r) => r.data),

  createKitchenStation: (body: unknown) =>
    apiClient
      .post<unknown>("/api/v1/settings/product/stations", body)
      .then((r) => r.data),

  updateInventoryPolicy: (body: unknown) =>
    apiClient
      .patch<unknown>("/api/v1/settings/product/inventory-policy", body)
      .then((r) => r.data),
};

// ─── Staff ────────────────────────────────────────────────────────────────────
export const staffApi = {
  listStaff: (params?: { branch_id?: number; role?: string }) =>
    apiClient
      .get<import("../src/schema").components["schemas"]["StaffRead"][]>(
        "/api/v1/staff",
        { params }
      )
      .then((r) => r.data),

  inviteStaff: (
    body: import("../src/schema").components["schemas"]["StaffInviteRequest"]
  ) =>
    apiClient.post<unknown>("/api/v1/staff", body).then((r) => r.data),

  updateStaff: (
    staffId: number,
    body: import("../src/schema").components["schemas"]["StaffUpdateRequest"]
  ) =>
    apiClient
      .put<import("../src/schema").components["schemas"]["StaffRead"]>(
        `/api/v1/staff/${staffId}`,
        body
      )
      .then((r) => r.data),

  disableStaff: (staffId: number) =>
    apiClient
      .delete(`/api/v1/staff/${staffId}`)
      .then((r) => r.data),

  setPin: (
    staffId: number,
    body: import("../src/schema").components["schemas"]["AdminSetPinRequest"]
  ) =>
    apiClient
      .post<void>(`/api/v1/staff/${staffId}/pin`, body)
      .then((r) => r.data),

  resetPin: (staffId: number) =>
    apiClient
      .delete(`/api/v1/staff/${staffId}/pin`)
      .then((r) => r.data),

  unlockPin: (staffId: number) =>
    apiClient
      .post<void>(`/api/v1/staff/${staffId}/pin/unlock`, {})
      .then((r) => r.data),
};

// ─── Print ────────────────────────────────────────────────────────────────────
export const printApi = {
  printReceipt: (orderId: number) =>
    apiClient
      .post<unknown>(`/api/v1/print/receipt/${orderId}`, {})
      .then((r) => r.data),

  reprintReceipt: (orderId: number) =>
    apiClient
      .post<unknown>(`/api/v1/print/receipt/${orderId}/reprint`, {})
      .then((r) => r.data),

  printZReport: (params: { branch_id: number; report_date: string }) =>
    apiClient
      .post<unknown>("/api/v1/print/z-report", {}, { params })
      .then((r) => r.data),

  listPrintJobs: (params?: { branch_id?: number }) =>
    apiClient
      .get<unknown[]>("/api/v1/print/jobs", { params })
      .then((r) => r.data),
};