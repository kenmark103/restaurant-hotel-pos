import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  createCategory,
  createMenuItem,
  type CreateCategoryPayload,
  type CreateMenuItemPayload,
  getMenu,
  updateMenuItem,
  type UpdateMenuItemPayload,
} from '@/features/menu/api/menuApi'
import type { MenuCategory, MenuItem } from '@/features/menu/types'

export const menuQueryKeys = {
  list: (branchId?: number | null) => ['menu', branchId ?? 'all'] as const,
}

function appendCategoryToTree(categories: MenuCategory[], created: MenuCategory): MenuCategory[] {
  if (created.parent_id == null) {
    return [...categories, created]
  }

  let attached = false

  const attach = (nodes: MenuCategory[]): MenuCategory[] =>
    nodes.map((node) => {
      if (node.id === created.parent_id) {
        attached = true
        return {
          ...node,
          children: [...(node.children ?? []), created],
        }
      }

      if (!node.children?.length) {
        return node
      }

      return {
        ...node,
        children: attach(node.children),
      }
    })

  const next = attach(categories)
  return attached ? next : [...categories, created]
}

function updateItemInTree(categories: MenuCategory[], item: MenuItem): MenuCategory[] {
  return categories.map((category) => {
    if (category.id === item.category_id) {
      const existing = category.items?.some((it) => it.id === item.id)
      return {
        ...category,
        items: existing
          ? (category.items ?? []).map((it) => (it.id === item.id ? item : it))
          : [...(category.items ?? []), item],
      }
    }

    if (!category.children?.length) {
      return category
    }

    return {
      ...category,
      children: updateItemInTree(category.children, item),
    }
  })
}

export function useMenu(branchId?: number | null) {
  return useQuery({
    queryKey: menuQueryKeys.list(branchId),
    queryFn: () => getMenu(branchId),
    staleTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}

export function useCreateCategory(branchId?: number | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateCategoryPayload) => createCategory(payload),
    onSuccess: (createdCategory) => {
      queryClient.setQueryData<MenuCategory[]>(menuQueryKeys.list(branchId), (current = []) =>
        appendCategoryToTree(current, createdCategory),
      )
    },
  })
}

export function useCreateMenuItem(branchId?: number | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateMenuItemPayload) => createMenuItem(payload),
    onSuccess: (createdItem) => {
      queryClient.setQueryData<MenuCategory[]>(menuQueryKeys.list(branchId), (current = []) =>
        updateItemInTree(current, createdItem),
      )
    },
  })
}

export function useUpdateMenuItem(branchId?: number | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ itemId, payload }: { itemId: number; payload: UpdateMenuItemPayload }) =>
      updateMenuItem(itemId, payload),
    onSuccess: (updatedItem) => {
      queryClient.setQueryData<MenuCategory[]>(menuQueryKeys.list(branchId), (current = []) =>
        updateItemInTree(current, updatedItem),
      )
    },
  })
}
