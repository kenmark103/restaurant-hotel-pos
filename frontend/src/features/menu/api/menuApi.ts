import { apiClient } from '@/shared/api/client'

import type { MenuCategory, MenuItem, MenuItemVariant, Station } from '../types'

export async function getMenu(branchId?: number | null) {
  const suffix = branchId != null ? `?branch_id=${branchId}` : ''
  const response = await apiClient.get<MenuCategory[]>(`/menu${suffix}`)
  return response.data
}

export interface CreateCategoryPayload {
  branch_id: number | null
  parent_id?: number | null
  name: string
  description?: string | null
  display_order?: number
  available_from?: string | null
  available_until?: string | null
}

export interface CreateMenuItemPayload {
  category_id: number
  name: string
  description?: string | null
  base_price: string
  cost_price?: string | null
  image_url?: string | null
  sku?: string | null
  barcode?: string | null
  unit_of_measure?: string
  track_inventory?: boolean
  low_stock_threshold?: number | null
  is_available?: boolean
  prep_time_minutes?: number
  station?: Station
  variants?: Array<{
    name: string
    sell_price: string
    cost_price?: string | null
    barcode?: string | null
    sku?: string | null
    display_order?: number
    is_default?: boolean
  }>
}

export interface UpdateMenuItemPayload {
  name?: string
  description?: string | null
  base_price?: string
  cost_price?: string | null
  image_url?: string | null
  sku?: string | null
  barcode?: string | null
  unit_of_measure?: string
  track_inventory?: boolean
  low_stock_threshold?: number | null
  is_available?: boolean
  prep_time_minutes?: number
  station?: Station
}

export interface CreateVariantPayload {
  name: string
  sell_price: string
  cost_price?: string | null
  barcode?: string | null
  sku?: string | null
  display_order?: number
  is_default?: boolean
}

export interface UpdateVariantPayload {
  name?: string
  sell_price?: string
  cost_price?: string | null
  barcode?: string | null
  sku?: string | null
  display_order?: number
  is_default?: boolean
  is_active?: boolean
}

export async function createCategory(payload: CreateCategoryPayload) {
  const response = await apiClient.post<MenuCategory>('/menu/categories', payload)
  return response.data
}

export async function createMenuItem(payload: CreateMenuItemPayload) {
  const response = await apiClient.post<MenuItem>('/menu/items', payload)
  return response.data
}

export async function updateMenuItem(itemId: number, payload: UpdateMenuItemPayload) {
  const response = await apiClient.patch<MenuItem>(`/menu/items/${itemId}`, payload)
  return response.data
}

export async function createVariant(itemId: number, payload: CreateVariantPayload) {
  const response = await apiClient.post<MenuItemVariant>(`/menu/items/${itemId}/variants`, payload)
  return response.data
}

export async function updateVariant(variantId: number, payload: UpdateVariantPayload) {
  const response = await apiClient.patch<MenuItemVariant>(`/menu/variants/${variantId}`, payload)
  return response.data
}

export async function deleteVariant(variantId: number) {
  await apiClient.delete(`/menu/variants/${variantId}`)
}
