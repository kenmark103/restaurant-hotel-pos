import { apiClient } from "../src/client";
import type { components } from "../src/schema";

type CategoryRead = components["schemas"]["CategoryRead"];
type CategoryCreate = components["schemas"]["CategoryCreate"];
type CategoryUpdate = components["schemas"]["CategoryUpdate"];
type CategoryReorderPayload =
  components["schemas"]["CategoryReorderPayload"];
type MenuItemRead = components["schemas"]["MenuItemRead"];
type MenuItemCreate = components["schemas"]["MenuItemCreate"];
type MenuItemUpdate = components["schemas"]["MenuItemUpdate"];
type ModifierGroupCreate = components["schemas"]["ModifierGroupCreate"];
type ModifierGroupUpdate = components["schemas"]["ModifierGroupUpdate"];
type ModifierOptionCreate = components["schemas"]["ModifierOptionCreate"];
type ModifierOptionUpdate = components["schemas"]["ModifierOptionUpdate"];
type KitchenStationResponse =
  components["schemas"]["KitchenStationResponse"];

export const productsApi = {
  // ── Public / POS menu ────────────────────────────────────────────────────
  getPublicMenu: (params: { branch_id?: number }) =>
    apiClient
      .get<CategoryRead[]>("/api/v1/products/public-menu", { params })
      .then((r) => r.data),

  // ── Categories ───────────────────────────────────────────────────────────
  getCategoryTree: (params?: { branch_id?: number }) =>
    apiClient
      .get<CategoryRead[]>("/api/v1/products/categories", { params })
      .then((r) => r.data),

  createCategory: (body: CategoryCreate) =>
    apiClient
      .post<CategoryRead>("/api/v1/products/categories", body)
      .then((r) => r.data),

  updateCategory: (categoryId: number, body: CategoryUpdate) =>
    apiClient
      .patch<CategoryRead>(
        `/api/v1/products/categories/${categoryId}`,
        body
      )
      .then((r) => r.data),

  deleteCategory: (categoryId: number) =>
    apiClient
      .delete(`/api/v1/products/categories/${categoryId}`)
      .then((r) => r.data),

  reorderCategories: (body: CategoryReorderPayload) =>
    apiClient
      .post<void>("/api/v1/products/categories/reorder", body)
      .then((r) => r.data),

  // ── Menu Items ───────────────────────────────────────────────────────────
  getItem: (itemId: number) =>
    apiClient
      .get<MenuItemRead>(`/api/v1/products/items/${itemId}`)
      .then((r) => r.data),

  createItem: (body: MenuItemCreate) =>
    apiClient
      .post<MenuItemRead>("/api/v1/products/items", body)
      .then((r) => r.data),

  updateItem: (itemId: number, body: MenuItemUpdate) =>
    apiClient
      .patch<MenuItemRead>(`/api/v1/products/items/${itemId}`, body)
      .then((r) => r.data),

  deleteItem: (itemId: number) =>
    apiClient
      .delete(`/api/v1/products/items/${itemId}`)
      .then((r) => r.data),

  toggleAvailability: (itemId: number) =>
    apiClient
      .patch<MenuItemRead>(
        `/api/v1/products/items/${itemId}/availability`,
        {}
      )
      .then((r) => r.data),

  searchItems: (params: { q: string; branch_id?: number }) =>
    apiClient
      .get<MenuItemRead[]>("/api/v1/products/items/search", { params })
      .then((r) => r.data),

  lookupByBarcode: (barcode: string) =>
    apiClient
      .get<MenuItemRead>(
        `/api/v1/products/items/barcode/${encodeURIComponent(barcode)}`
      )
      .then((r) => r.data),

  // ── Modifier Groups ───────────────────────────────────────────────────────
  addModifierGroup: (itemId: number, body: ModifierGroupCreate) =>
    apiClient
      .post<MenuItemRead>(
        `/api/v1/products/items/${itemId}/modifier-groups`,
        body
      )
      .then((r) => r.data),

  updateModifierGroup: (groupId: number, body: ModifierGroupUpdate) =>
    apiClient
      .patch<void>(
        `/api/v1/products/modifier-groups/${groupId}`,
        body
      )
      .then((r) => r.data),

  deleteModifierGroup: (groupId: number) =>
    apiClient
      .delete(`/api/v1/products/modifier-groups/${groupId}`)
      .then((r) => r.data),

  addModifierOption: (groupId: number, body: ModifierOptionCreate) =>
    apiClient
      .post<void>(
        `/api/v1/products/modifier-groups/${groupId}/options`,
        body
      )
      .then((r) => r.data),

  updateModifierOption: (
    optionId: number,
    body: ModifierOptionUpdate
  ) =>
    apiClient
      .patch<void>(
        `/api/v1/products/modifier-options/${optionId}`,
        body
      )
      .then((r) => r.data),

  deleteModifierOption: (optionId: number) =>
    apiClient
      .delete(`/api/v1/products/modifier-options/${optionId}`)
      .then((r) => r.data),

  // ── Stations (read-only list for item assignment) ────────────────────────
  listStationsForItems: () =>
    apiClient
      .get<KitchenStationResponse[]>("/api/v1/products/stations")
      .then((r) => r.data),
};