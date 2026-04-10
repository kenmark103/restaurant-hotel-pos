import { type FormEvent, useEffect, useMemo, useState } from 'react'

import { AddCategoryPanel, type AddCategoryForm } from '@/features/menu/components/AddCategoryPanel'
import { AddItemPanel, type AddItemForm } from '@/features/menu/components/AddItemPanel'
import { CategoryTabs } from '@/features/menu/components/CategoryTabs'
import { EditItemDrawer, type EditItemForm } from '@/features/menu/components/EditItemDrawer'
import { MenuItemCard } from '@/features/menu/components/MenuItemCard'
import { useCreateCategory, useCreateMenuItem, useMenu, useUpdateMenuItem } from '@/features/menu/hooks/useMenu'
import { flattenCategoryIds, flattenMenuItems, type MenuCategory, type MenuItemWithCategory, type Station } from '@/features/menu/types'
import { useBranches } from '@/features/staff/hooks/useBranches'
import { useSettings } from '@/contexts/SettingsContext'
import { Button } from '@/shared/ui/Button'
import { Spinner } from '@/shared/ui/Spinner'

const BLANK_CATEGORY_FORM: AddCategoryForm = {
  name: '',
  description: '',
  display_order: '0',
}

const BLANK_ITEM_FORM: AddItemForm = {
  category_id: '',
  name: '',
  description: '',
  base_price: '',
  prep_time_minutes: '10',
  station: 'any',
  sku: '',
}

export function MenuPage() {
  const { formatPrice } = useSettings()
  const { data: branches, isLoading: branchesLoading } = useBranches()

  const [selectedBranchId, setSelectedBranchId] = useState<number | null>(null)
  const [activeCategoryId, setActiveCategoryId] = useState<number | 'all'>('all')
  const [panel, setPanel] = useState<'none' | 'add-category' | 'add-item'>('none')
  const [actionError, setActionError] = useState<string | null>(null)

  const [categoryForm, setCategoryForm] = useState(BLANK_CATEGORY_FORM)
  const [itemForm, setItemForm] = useState(BLANK_ITEM_FORM)

  const [editingItem, setEditingItem] = useState<MenuItemWithCategory | null>(null)
  const [editForm, setEditForm] = useState<EditItemForm | null>(null)

  const { data: categories, isLoading: menuLoading } = useMenu(selectedBranchId)
  const createCategoryMutation = useCreateCategory(selectedBranchId)
  const createMenuItemMutation = useCreateMenuItem(selectedBranchId)
  const updateMenuItemMutation = useUpdateMenuItem(selectedBranchId)

  useEffect(() => {
    if (selectedBranchId != null || !branches?.length) {
      return
    }
    setSelectedBranchId(branches[0].id)
  }, [branches, selectedBranchId])

  const allItems = useMemo<MenuItemWithCategory[]>(() => flattenMenuItems(categories ?? []), [categories])

  const categoryTreeIndex = useMemo(() => {
    const map = new Map<number, number[]>()

    const walk = (category: MenuCategory) => {
      map.set(category.id, flattenCategoryIds(category))
      for (const child of category.children ?? []) {
        walk(child)
      }
    }

    for (const category of categories ?? []) {
      walk(category)
    }

    return map
  }, [categories])

  const displayedItems = useMemo(() => {
    if (activeCategoryId === 'all') {
      return allItems
    }
    const categoryIds = new Set(categoryTreeIndex.get(activeCategoryId) ?? [activeCategoryId])
    return allItems.filter((item) => categoryIds.has(item.category_id))
  }, [activeCategoryId, allItems, categoryTreeIndex])

  const isLoading = branchesLoading || menuLoading

  const handleCreateCategory = async (event: FormEvent) => {
    event.preventDefault()
    setActionError(null)

    try {
      await createCategoryMutation.mutateAsync({
        branch_id: selectedBranchId,
        name: categoryForm.name,
        description: categoryForm.description || null,
        display_order: Number(categoryForm.display_order),
      })
      setCategoryForm(BLANK_CATEGORY_FORM)
      setPanel('none')
    } catch (error) {
      setActionError(getErrorMessage(error))
    }
  }

  const handleCreateItem = async (event: FormEvent) => {
    event.preventDefault()
    if (!itemForm.category_id) {
      return
    }

    setActionError(null)
    try {
      await createMenuItemMutation.mutateAsync({
        category_id: Number(itemForm.category_id),
        name: itemForm.name,
        description: itemForm.description || null,
        base_price: itemForm.base_price,
        prep_time_minutes: Number(itemForm.prep_time_minutes),
        station: itemForm.station,
        sku: itemForm.sku || null,
      })
      setItemForm(BLANK_ITEM_FORM)
      setPanel('none')
    } catch (error) {
      setActionError(getErrorMessage(error))
    }
  }

  const openEditDrawer = (item: MenuItemWithCategory) => {
    setEditingItem(item)
    setEditForm({
      name: item.name,
      description: item.description ?? '',
      base_price: item.base_price,
      prep_time_minutes: String(item.prep_time_minutes),
      station: (item.station ?? 'any') as Station,
      sku: item.sku ?? '',
      image_url: item.image_url ?? '',
      is_available: item.is_available,
    })
  }

  const closeEditDrawer = () => {
    setEditingItem(null)
    setEditForm(null)
  }

  const handleSaveItem = async (event: FormEvent) => {
    event.preventDefault()
    if (!editingItem || !editForm) {
      return
    }

    setActionError(null)
    try {
      await updateMenuItemMutation.mutateAsync({
        itemId: editingItem.id,
        payload: {
          name: editForm.name,
          description: editForm.description || null,
          base_price: editForm.base_price,
          prep_time_minutes: Number(editForm.prep_time_minutes),
          station: editForm.station,
          sku: editForm.sku || null,
          image_url: editForm.image_url || null,
          is_available: editForm.is_available,
        },
      })
      closeEditDrawer()
    } catch (error) {
      setActionError(getErrorMessage(error))
    }
  }

  const handleToggleAvailability = async (item: MenuItemWithCategory) => {
    setActionError(null)
    try {
      await updateMenuItemMutation.mutateAsync({
        itemId: item.id,
        payload: { is_available: !item.is_available },
      })
      if (editingItem?.id === item.id && editForm) {
        setEditForm({ ...editForm, is_available: !item.is_available })
      }
    } catch (error) {
      setActionError(getErrorMessage(error))
    }
  }

  if (isLoading) {
    return (
      <section className="app-panel p-8">
        <Spinner />
      </section>
    )
  }

  return (
    <>
      <section className="flex h-full min-h-0 flex-col gap-4">
        <div className="app-panel p-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="min-w-[180px]">
              <p className="app-label mb-1">Branch</p>
              <select
                className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm text-ink"
                value={selectedBranchId ?? ''}
                onChange={(event) => {
                  setSelectedBranchId(event.target.value ? Number(event.target.value) : null)
                  setActiveCategoryId('all')
                }}
              >
                {branches?.map((branch) => (
                  <option key={branch.id} value={branch.id}>
                    {branch.name}
                  </option>
                ))}
              </select>
            </div>

            <CategoryTabs
              categories={
                categories?.map((category) => ({
                  id: category.id,
                  name: category.name,
                  itemCount: allItems.filter((item) => (categoryTreeIndex.get(category.id) ?? []).includes(item.category_id))
                    .length,
                })) ?? []
              }
              activeId={activeCategoryId}
              totalCount={allItems.length}
              onChange={setActiveCategoryId}
            />

            <div className="flex items-center gap-2">
              <button
                className="rounded-xl border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-appbg"
                type="button"
                onClick={() => setPanel((current) => (current === 'add-category' ? 'none' : 'add-category'))}
              >
                Add category
              </button>
              <Button type="button" onClick={() => setPanel((current) => (current === 'add-item' ? 'none' : 'add-item'))}>
                Add item
              </Button>
            </div>
          </div>

          {actionError ? <p className="mt-3 text-sm text-danger">{actionError}</p> : null}
        </div>

        {panel === 'add-category' ? (
          <AddCategoryPanel
            form={categoryForm}
            isBusy={createCategoryMutation.isPending || !selectedBranchId}
            onChange={setCategoryForm}
            onSubmit={handleCreateCategory}
            onClose={() => setPanel('none')}
          />
        ) : null}

        {panel === 'add-item' ? (
          <AddItemPanel
            categories={categories ?? []}
            form={itemForm}
            isBusy={createMenuItemMutation.isPending || !selectedBranchId}
            onChange={setItemForm}
            onSubmit={handleCreateItem}
            onClose={() => setPanel('none')}
          />
        ) : null}

        {displayedItems.length === 0 ? (
          <div className="app-panel flex flex-1 items-center justify-center p-8">
            <div className="text-center">
              <p className="text-base font-semibold text-ink">No items yet</p>
              <p className="mt-1 text-sm text-muted">Create a category and add items to manage your menu.</p>
              <div className="mt-4">
                <Button onClick={() => setPanel('add-item')} type="button">
                  Add first item
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {displayedItems.map((item) => (
              <MenuItemCard
                key={item.id}
                item={item}
                formatPrice={formatPrice}
                isBusy={updateMenuItemMutation.isPending}
                onEdit={() => openEditDrawer(item)}
                onToggle={() => void handleToggleAvailability(item)}
              />
            ))}
          </div>
        )}
      </section>

      {editingItem && editForm ? (
        <EditItemDrawer
          form={editForm}
          isBusy={updateMenuItemMutation.isPending}
          item={editingItem}
          onChange={setEditForm}
          onClose={closeEditDrawer}
          onSubmit={handleSaveItem}
        />
      ) : null}
    </>
  )
}

function getErrorMessage(error: unknown): string {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response
    if (response?.data?.detail) {
      return response.data.detail
    }
  }
  return 'Action failed. Please try again.'
}
