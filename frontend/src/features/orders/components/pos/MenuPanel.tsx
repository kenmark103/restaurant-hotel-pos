/**
 * features/orders/components/pos/MenuPanel.tsx
 *
 * Changes from original:
 * - Shows VariantSelector modal when a tapped item has active variants
 * - Barcode scan button activates the scanner hook
 * - Passes variant_id to onAddItem callback
 */

import { useState } from 'react'
import { MenuItemTile } from '@/features/menu/components/MenuItemTile'
import { VariantSelector } from './VariantSelector'
import { useBarcodeScanner } from '@/shared/hooks/useBarcodeScanner'
import type { MenuItem, MenuItemVariant, MenuItemWithCategory } from '@/features/menu/types'

interface CategoryTab {
  id: number
  name: string
  count: number
}

interface MenuPanelProps {
  className?: string
  categories: CategoryTab[]
  items: MenuItemWithCategory[]
  activeCategoryId: number | 'all'
  quantityMap: Map<number, number>
  hasActiveOrder: boolean
  isWorking: boolean
  isOrderOpen: boolean
  formatPrice: (v: number | string) => string
  onCategoryChange: (id: number | 'all') => void
  onAddItem: (item: MenuItemWithCategory, variantId?: number) => void
  onBarcodeScanned?: (barcode: string) => void
}

export function MenuPanel({
  className = '',
  categories,
  items,
  activeCategoryId,
  quantityMap,
  hasActiveOrder,
  isWorking,
  isOrderOpen,
  formatPrice,
  onCategoryChange,
  onAddItem,
  onBarcodeScanned,
}: MenuPanelProps) {
  const [pendingItem, setPendingItem] = useState<MenuItemWithCategory | null>(null)

  const { isListening, startListening, stopListening } = useBarcodeScanner({
    onScan: (barcode) => {
      stopListening()
      onBarcodeScanned?.(barcode)
    },
  })

  const handleTileClick = (item: MenuItemWithCategory) => {
    if (!hasActiveOrder || !isOrderOpen) return
    const activeVariants = item.variants.filter((v) => v.is_active)
    if (activeVariants.length > 0) {
      setPendingItem(item)
    } else {
      onAddItem(item)
    }
  }

  const handleVariantSelect = (item: MenuItemWithCategory, variant: MenuItemVariant) => {
    setPendingItem(null)
    onAddItem(item, variant.id)
  }

  return (
    <section className={`flex flex-col rounded-xl border border-line bg-panel ${className}`}>
      {/* Category tabs */}
      <div className="shrink-0 border-b border-line px-3 py-2.5">
        <div className="flex items-center gap-2">
          <div className="flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto">
            <CategoryPill
              active={activeCategoryId === 'all'}
              onClick={() => onCategoryChange('all')}
            >
              All ({items.length})
            </CategoryPill>
            {categories.map((cat) => (
              <CategoryPill
                key={cat.id}
                active={activeCategoryId === cat.id}
                onClick={() => onCategoryChange(cat.id)}
              >
                {cat.name} ({cat.count})
              </CategoryPill>
            ))}
          </div>

          {/* Barcode scanner toggle */}
          {onBarcodeScanned && (
            <button
              type="button"
              title={isListening ? 'Stop scanning' : 'Scan barcode'}
              onClick={isListening ? stopListening : startListening}
              className={`shrink-0 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition ${
                isListening
                  ? 'border-accent bg-accent text-white animate-pulse'
                  : 'border-line bg-white text-muted hover:border-accent hover:text-ink'
              }`}
            >
              {isListening ? '📡 Scanning…' : '📷 Scan'}
            </button>
          )}
        </div>
      </div>

      {/* Item grid */}
      <div className="flex-1 overflow-y-auto p-3">
        {!hasActiveOrder ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted">Select a table to start a ticket</p>
          </div>
        ) : items.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted">No items in this category</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
            {items.map((item) => (
              <MenuItemTile
                key={item.id}
                item={item}
                quantityInTicket={quantityMap.get(item.id) ?? 0}
                formatPrice={formatPrice}
                disabled={isWorking || !isOrderOpen}
                onAdd={() => handleTileClick(item)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Variant selector modal */}
      {pendingItem && (
        <VariantSelector
          item={pendingItem}
          formatPrice={formatPrice}
          onSelect={handleVariantSelect}
          onClose={() => setPendingItem(null)}
        />
      )}
    </section>
  )
}

function CategoryPill({
  active,
  children,
  onClick,
}: {
  active: boolean
  children: React.ReactNode
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`shrink-0 rounded-xl border px-3 py-1.5 text-xs font-semibold transition ${
        active
          ? 'border-accent bg-accent/10 text-accent'
          : 'border-line bg-white text-muted hover:border-accent/40 hover:text-ink'
      }`}
    >
      {children}
    </button>
  )
}