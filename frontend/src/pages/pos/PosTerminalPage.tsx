import { useEffect, useMemo, useRef, useState } from 'react'

import { useSettings } from '@/contexts/SettingsContext'
import { useMenu } from '@/features/menu/hooks/useMenu'
import { flattenCategoryIds, flattenMenuItems, type MenuCategory, type MenuItem } from '@/features/menu/types'
import { LineNoteModal } from '@/features/orders/components/pos/LineNoteModal'
import { MenuPanel } from '@/features/orders/components/pos/MenuPanel'
import { TableGrid, type TableWithOrder } from '@/features/orders/components/pos/TableGrid'
import { TicketPanel } from '@/features/orders/components/pos/TicketPanel'
import {
  useActiveOrders,
  useAddOrderItem,
  useCloseOrder,
  useCreateOrder,
  useHoldOrder,
  useOrderDetail,
  useSendOrder,
  useUpdateOrderItem,
  useVoidOrder,
  useVoidOrderItem,
} from '@/features/orders/hooks/useOrders'
import type { PaymentMethod, PosOrder, PosOrderItem } from '@/features/orders/types'
import { useBranches } from '@/features/staff/hooks/useBranches'
import { useTables } from '@/features/tables/hooks/useTables'
import { AppSelect } from '@/shared/ui/AppSelect'
import { Spinner } from '@/shared/ui/Spinner'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { usePosStore } from '@/store/posStore'

type MenuItemWithCategory = MenuItem & { categoryName: string }

type NoteEditorState = {
  itemId: number
  itemName: string
  quantity: number
  note: string
}

type MobilePanel = 'tables' | 'menu' | 'ticket'

export function PosTerminalPage() {
  const { formatPrice } = useSettings()
  const storedBranchId = usePosStore((state) => state.activeBranchId)
  const setStoredBranchId = usePosStore((state) => state.setActiveBranchId)

  const [selectedBranchId, setSelectedBranchId] = useState<number | null>(storedBranchId)
  const [activeOrderId, setActiveOrderId] = useState<number | null>(null)
  const [activeCategoryId, setActiveCategoryId] = useState<number | 'all'>('all')
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('cash')
  const [amountPaid, setAmountPaid] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)
  const [noteEditor, setNoteEditor] = useState<NoteEditorState | null>(null)
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>('tables')

  const holdTimerRef = useRef<number | null>(null)

  const { data: branches, isLoading: branchesLoading } = useBranches()
  const { data: tables, isLoading: tablesLoading } = useTables(selectedBranchId)
  const { data: categories, isLoading: menuLoading } = useMenu(selectedBranchId)
  const { data: activeOrders, isLoading: ordersLoading } = useActiveOrders(selectedBranchId)
  const { data: activeOrderDetail } = useOrderDetail(activeOrderId)

  const createOrderMutation = useCreateOrder(selectedBranchId)
  const addItemMutation = useAddOrderItem(selectedBranchId)
  const updateItemMutation = useUpdateOrderItem(selectedBranchId)
  const voidItemMutation = useVoidOrderItem(selectedBranchId)
  const sendOrderMutation = useSendOrder(selectedBranchId)
  const holdOrderMutation = useHoldOrder(selectedBranchId)
  const voidOrderMutation = useVoidOrder(selectedBranchId)
  const closeOrderMutation = useCloseOrder(selectedBranchId)

  useEffect(() => {
    if (selectedBranchId != null) {
      setStoredBranchId(selectedBranchId)
      return
    }

    if (!branches?.length) {
      return
    }

    const branchFromStore = branches.find((branch) => branch.id === storedBranchId)
    setSelectedBranchId(branchFromStore?.id ?? branches[0].id)
  }, [branches, selectedBranchId, setStoredBranchId, storedBranchId])

  const activeOrder = activeOrderDetail ?? activeOrders?.find((order) => order.id === activeOrderId) ?? null

  useEffect(() => {
    if (!activeOrder) {
      setAmountPaid('')
      setNoteEditor(null)
      return
    }

    setAmountPaid(Number(activeOrder.total_amount).toFixed(2))
  }, [activeOrder?.id, activeOrder?.total_amount])

  useEffect(() => {
    if (activeOrder && mobilePanel === 'tables') {
      setMobilePanel('menu')
    }
  }, [activeOrder, mobilePanel])

  const menuItems = useMemo(
    () => flattenMenuItems(categories ?? []).filter((item) => item.is_available),
    [categories],
  )

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

  const categoryTabs = useMemo(
    () =>
      categories?.map((category) => ({
        id: category.id,
        name: category.name,
        count: menuItems.filter((item) => (categoryTreeIndex.get(category.id) ?? []).includes(item.category_id)).length,
      })) ?? [],
    [categories, categoryTreeIndex, menuItems],
  )

  useEffect(() => {
    if (activeCategoryId === 'all') {
      return
    }

    const exists = categoryTabs.some((category) => category.id === activeCategoryId && category.count > 0)
    if (!exists) {
      setActiveCategoryId('all')
    }
  }, [activeCategoryId, categoryTabs])

  const displayedMenuItems = useMemo(() => {
    if (activeCategoryId === 'all') {
      return menuItems
    }
    const categoryIds = new Set(categoryTreeIndex.get(activeCategoryId) ?? [activeCategoryId])
    return menuItems.filter((item) => categoryIds.has(item.category_id))
  }, [activeCategoryId, categoryTreeIndex, menuItems])

  const tablesWithOrders = useMemo<TableWithOrder[]>(() => {
    const orderByTable = new Map<number, PosOrder>()
    activeOrders?.forEach((order) => {
      if (order.table_id != null) {
        orderByTable.set(order.table_id, order)
      }
    })

    return (tables ?? []).map((table) => ({
      ...table,
      activeOrder: orderByTable.get(table.id) ?? null,
    }))
  }, [activeOrders, tables])

  const ticketItems = useMemo(() => (activeOrder?.items ?? []).filter((item) => !item.is_voided), [activeOrder])

  const quantityMap = useMemo(() => {
    const map = new Map<number, number>()
    ticketItems.forEach((line) => map.set(line.menu_item_id, line.quantity))
    return map
  }, [ticketItems])

  const isWorking =
    createOrderMutation.isPending ||
    addItemMutation.isPending ||
    updateItemMutation.isPending ||
    voidItemMutation.isPending ||
    sendOrderMutation.isPending ||
    holdOrderMutation.isPending ||
    voidOrderMutation.isPending ||
    closeOrderMutation.isPending

  const isLoading = branchesLoading || tablesLoading || menuLoading || ordersLoading

  const totalAmount = Number(activeOrder?.total_amount ?? 0)
  const amountPaidNumber = Number.isFinite(Number(amountPaid)) ? Number(amountPaid) : 0
  const changeDue = paymentMethod === 'cash' ? Math.max(amountPaidNumber - totalAmount, 0) : 0

  const canClose =
    activeOrder != null &&
    (activeOrder.status === 'open' || activeOrder.status === 'sent') &&
    Number.isFinite(Number(amountPaid)) &&
    amountPaidNumber >= totalAmount

  useEffect(() => {
    return () => {
      if (holdTimerRef.current) {
        clearTimeout(holdTimerRef.current)
      }
    }
  }, [])

  const handleSelectBranch = (branchId: number | null) => {
    setSelectedBranchId(branchId)
    setActiveOrderId(null)
    setActiveCategoryId('all')
    setActionError(null)
    setMobilePanel('tables')
  }

  const handleOpenOrCreateOrder = async (table: TableWithOrder) => {
    setActionError(null)

    if (table.activeOrder) {
      setActiveOrderId(table.activeOrder.id)
      return
    }

    try {
      const order = await createOrderMutation.mutateAsync({ table_id: table.id, order_type: 'dine_in' })
      setActiveOrderId(order.id)
    } catch (error) {
      setActionError(getErrorMessage(error))
    }
  }

  const handleAddItem = async (item: MenuItemWithCategory, variantId?: number) => {
    if (!activeOrder) {
      return
    }

    setActionError(null)
    try {
      await addItemMutation.mutateAsync({
        orderId: activeOrder.id,
        payload: { menu_item_id: item.id, variant_id: variantId, quantity: 1 },
      })
    } catch (error) {
      setActionError(getErrorMessage(error))
    }
  }

  const handleIncrementItem = async (line: PosOrderItem) => {
    if (!activeOrder) {
      return
    }

    setActionError(null)
    try {
      await updateItemMutation.mutateAsync({
        orderId: activeOrder.id,
        itemId: line.id,
        payload: { quantity: line.quantity + 1, note: line.note ?? null },
      })
    } catch (error) {
      setActionError(getErrorMessage(error))
    }
  }

  const handleDecrementItem = async (line: PosOrderItem) => {
    if (!activeOrder) {
      return
    }

    setActionError(null)
    try {
      if (line.quantity <= 1) {
        await voidItemMutation.mutateAsync({
          orderId: activeOrder.id,
          itemId: line.id,
          payload: { reason: 'Removed from ticket.' },
        })
        return
      }

      await updateItemMutation.mutateAsync({
        orderId: activeOrder.id,
        itemId: line.id,
        payload: { quantity: line.quantity - 1, note: line.note ?? null },
      })
    } catch (error) {
      setActionError(getErrorMessage(error))
    }
  }

  const handleVoidLine = async (line: PosOrderItem) => {
    if (!activeOrder) {
      return
    }

    setActionError(null)
    try {
      await voidItemMutation.mutateAsync({
        orderId: activeOrder.id,
        itemId: line.id,
        payload: { reason: 'Voided by operator.' },
      })
    } catch (error) {
      setActionError(getErrorMessage(error))
    }
  }

  const handleSendOrHold = async () => {
    if (!activeOrder) {
      return
    }

    setActionError(null)
    try {
      if (activeOrder.status === 'open') {
        await sendOrderMutation.mutateAsync(activeOrder.id)
      } else if (activeOrder.status === 'sent') {
        await holdOrderMutation.mutateAsync(activeOrder.id)
      }
    } catch (error) {
      setActionError(getErrorMessage(error))
    }
  }

  const handleVoidOrder = async () => {
    if (!activeOrder) {
      return
    }

    setActionError(null)
    try {
      await voidOrderMutation.mutateAsync({
        orderId: activeOrder.id,
        payload: { reason: 'Voided from POS terminal.' },
      })
      setActiveOrderId(null)
      setMobilePanel('tables')
    } catch (error) {
      setActionError(getErrorMessage(error))
    }
  }

  const handleCloseOrder = async () => {
    if (!activeOrder) {
      return
    }

    setActionError(null)
    try {
      await closeOrderMutation.mutateAsync({
        orderId: activeOrder.id,
        payload: {
          payment_method: paymentMethod,
          amount_paid: amountPaidNumber.toFixed(2),
        },
      })
      setActiveOrderId(null)
      setMobilePanel('tables')
    } catch (error) {
      setActionError(getErrorMessage(error))
    }
  }

  const openLineNoteEditor = (line: PosOrderItem) => {
    setNoteEditor({
      itemId: line.id,
      itemName: line.menu_item_name,
      quantity: line.quantity,
      note: line.note ?? '',
    })
  }

  const handleLinePointerDown = (line: PosOrderItem) => {
    if (!activeOrder || activeOrder.status !== 'open') {
      return
    }

    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current)
    }

    holdTimerRef.current = window.setTimeout(() => {
      openLineNoteEditor(line)
      holdTimerRef.current = null
    }, 450)
  }

  const clearHoldTimer = () => {
    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current)
      holdTimerRef.current = null
    }
  }

  const handleSaveLineNote = async () => {
    if (!activeOrder || !noteEditor) {
      return
    }

    setActionError(null)
    try {
      await updateItemMutation.mutateAsync({
        orderId: activeOrder.id,
        itemId: noteEditor.itemId,
        payload: {
          quantity: noteEditor.quantity,
          note: noteEditor.note.trim() ? noteEditor.note.trim() : null,
        },
      })
      setNoteEditor(null)
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
      <div className="flex h-full min-h-0 flex-col gap-3">
        <div className="app-panel shrink-0 p-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="min-w-[220px]">
              <p className="app-label">POS terminal</p>
              <AppSelect
                value={selectedBranchId ?? ''}
                onChange={(event) => handleSelectBranch(event.target.value ? Number(event.target.value) : null)}
              >
                {branches?.map((branch) => (
                  <option key={branch.id} value={branch.id}>
                    {branch.name}
                  </option>
                ))}
              </AppSelect>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge label={`${tables?.length ?? 0} tables`} uppercase={false} />
              <StatusBadge label={`${activeOrders?.length ?? 0} live tickets`} tone="info" uppercase={false} />
              {activeOrder ? (
                <StatusBadge
                  label={`Ticket #${activeOrder.id} ${activeOrder.status}`}
                  tone={orderTone(activeOrder.status)}
                  uppercase={false}
                />
              ) : null}
            </div>

            {actionError ? <p className="text-sm text-danger">{actionError}</p> : null}
          </div>
        </div>

        <div className="flex min-h-0 flex-1 gap-3">
          <TableGrid
            className={`${mobilePanel === 'tables' ? 'flex' : 'hidden'} md:flex w-[260px] shrink-0`}
            tables={tablesWithOrders}
            activeOrderId={activeOrderId}
            isWorking={isWorking}
            onSelect={(table) => void handleOpenOrCreateOrder(table)}
          />
          <MenuPanel
            className={`${mobilePanel === 'menu' ? 'flex' : 'hidden'} md:flex flex-1`}
            categories={categoryTabs}
            items={displayedMenuItems}
            activeCategoryId={activeCategoryId}
            quantityMap={quantityMap}
            hasActiveOrder={activeOrder !== null}
            isWorking={isWorking}
            isOrderOpen={activeOrder?.status === 'open'}
            formatPrice={formatPrice}
            onCategoryChange={setActiveCategoryId}
            onAddItem={(item, variantId) => void handleAddItem(item, variantId)}
          />
          <TicketPanel
            className={`${mobilePanel === 'ticket' ? 'flex' : 'hidden'} md:flex w-[340px] shrink-0`}
            activeOrder={activeOrder}
            ticketItems={ticketItems}
            paymentMethod={paymentMethod}
            amountPaid={amountPaid}
            changeDue={changeDue}
            canClose={canClose}
            isWorking={isWorking}
            formatPrice={formatPrice}
            onSendOrHold={() => void handleSendOrHold()}
            onVoidOrder={() => void handleVoidOrder()}
            onCloseOrder={() => void handleCloseOrder()}
            onAmountChange={setAmountPaid}
            onMethodChange={setPaymentMethod}
            onItemIncrement={(item) => void handleIncrementItem(item)}
            onItemDecrement={(item) => void handleDecrementItem(item)}
            onItemVoid={(item) => void handleVoidLine(item)}
            onItemPointerDown={handleLinePointerDown}
            onItemPointerUp={clearHoldTimer}
            onItemPointerLeave={clearHoldTimer}
          />
        </div>

        <MobilePanelNav
          active={mobilePanel}
          ticketCount={ticketItems.length}
          hasActiveOrder={activeOrder !== null}
          onChange={setMobilePanel}
        />
      </div>

      {noteEditor ? (
        <LineNoteModal
          itemName={noteEditor.itemName}
          note={noteEditor.note}
          isBusy={updateItemMutation.isPending}
          onChange={(note) => setNoteEditor({ ...noteEditor, note })}
          onSave={() => void handleSaveLineNote()}
          onClose={() => setNoteEditor(null)}
        />
      ) : null}
    </>
  )
}

function MobilePanelNav({
  active,
  ticketCount,
  hasActiveOrder,
  onChange,
}: {
  active: MobilePanel
  ticketCount: number
  hasActiveOrder: boolean
  onChange: (p: MobilePanel) => void
}) {
  return (
    <nav className="shrink-0 flex items-center justify-around border-t border-line bg-panel py-2 md:hidden">
      <NavTab active={active === 'tables'} label="Tables" onClick={() => onChange('tables')} />
      <NavTab active={active === 'menu'} label="Menu" disabled={!hasActiveOrder} onClick={() => onChange('menu')} />
      <NavTab
        active={active === 'ticket'}
        label={ticketCount > 0 ? `Ticket (${ticketCount})` : 'Ticket'}
        disabled={!hasActiveOrder}
        onClick={() => onChange('ticket')}
      />
    </nav>
  )
}

function NavTab({
  active,
  label,
  disabled = false,
  onClick,
}: {
  active: boolean
  label: string
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
        active ? 'bg-accent text-white' : 'text-muted hover:text-ink'
      } disabled:cursor-not-allowed disabled:opacity-50`}
    >
      {label}
    </button>
  )
}

function orderTone(status: PosOrder['status']): 'neutral' | 'info' | 'success' | 'warning' | 'danger' {
  if (status === 'open') {
    return 'warning'
  }
  if (status === 'sent') {
    return 'info'
  }
  if (status === 'closed') {
    return 'success'
  }
  if (status === 'voided') {
    return 'danger'
  }
  return 'neutral'
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
