export type Station = 'any' | 'grill' | 'fryer' | 'bar' | 'cold' | 'pass'

export interface MenuItemVariant {
  id: number
  menu_item_id: number
  name: string
  sell_price: string
  cost_price: string | null
  barcode: string | null
  sku: string | null
  display_order: number
  is_default: boolean
  is_active: boolean
}

export interface MenuItem {
  id: number
  category_id: number
  name: string
  description: string | null
  image_url: string | null
  sku: string | null
  barcode: string | null
  base_price: string
  cost_price: string | null
  unit_of_measure: string
  track_inventory: boolean
  low_stock_threshold: number | null
  prep_time_minutes: number
  station: Station
  is_available: boolean
  variants: MenuItemVariant[]
}

export interface MenuCategory {
  id: number
  branch_id: number | null
  parent_id: number | null
  name: string
  description: string | null
  display_order: number
  is_active: boolean
  available_from: string | null
  available_until: string | null
  children: MenuCategory[]
  items: MenuItem[]
}

export interface MenuItemWithCategory extends MenuItem {
  categoryName: string
}

export interface CategoryOption {
  id: number
  name: string
  parent_id: number | null
  depth: number
}

export interface StockLevel {
  menu_item_id: number
  variant_id: number | null
  name: string
  variant_name: string | null
  current_stock: string
  unit_of_measure: string
  low_stock_threshold: number | null
  is_low: boolean
}

export function flattenCategories(
  categories: MenuCategory[],
  depth = 0,
  result: CategoryOption[] = [],
): CategoryOption[] {
  for (const category of categories) {
    const prefix = depth > 0 ? `${'-'.repeat(depth)} ` : ''
    result.push({
      id: category.id,
      name: `${prefix}${category.name}`,
      parent_id: category.parent_id,
      depth,
    })

    if (category.children?.length) {
      flattenCategories(category.children, depth + 1, result)
    }
  }

  return result
}

export function flattenMenuItems(categories: MenuCategory[]): MenuItemWithCategory[] {
  const result: MenuItemWithCategory[] = []

  const walk = (category: MenuCategory, parentTrail: string[] = []) => {
    const trail = [...parentTrail, category.name]
    const categoryName = trail.join(' > ')

    for (const item of category.items ?? []) {
      result.push({
        ...item,
        categoryName,
      })
    }

    for (const child of category.children ?? []) {
      walk(child, trail)
    }
  }

  for (const category of categories) {
    walk(category)
  }

  return result
}

export function flattenCategoryIds(category: MenuCategory): number[] {
  const ids = [category.id]

  for (const child of category.children ?? []) {
    ids.push(...flattenCategoryIds(child))
  }

  return ids
}
