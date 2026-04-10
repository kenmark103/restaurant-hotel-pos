import type { FormEvent } from 'react'

import { flattenCategories, type MenuCategory, type Station } from '@/features/menu/types'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'

export interface AddItemForm {
  category_id: string
  name: string
  description: string
  base_price: string
  prep_time_minutes: string
  station: Station
  sku: string
}

interface AddItemPanelProps {
  categories: MenuCategory[]
  form: AddItemForm
  isBusy: boolean
  onChange: (form: AddItemForm) => void
  onSubmit: (e: FormEvent) => void
  onClose: () => void
}

const STATION_LABELS: Record<Station, string> = {
  any: 'Any',
  grill: 'Grill',
  fryer: 'Fryer',
  bar: 'Bar',
  cold: 'Cold',
  pass: 'Pass',
}

export function AddItemPanel({ categories, form, isBusy, onChange, onSubmit, onClose }: AddItemPanelProps) {
  const categoryOptions = flattenCategories(categories)

  return (
    <div className="app-panel p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-ink">Create menu item</h2>
        <button
          type="button"
          className="rounded-lg border border-line px-2 py-1 text-xs font-semibold text-muted hover:text-ink"
          onClick={onClose}
        >
          Close
        </button>
      </div>
      <form className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" onSubmit={onSubmit}>
        <select
          className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm text-ink"
          required
          value={form.category_id}
          onChange={(event) => onChange({ ...form, category_id: event.target.value })}
        >
          <option value="">Category</option>
          {categoryOptions.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
        <Input
          placeholder="Item name"
          required
          value={form.name}
          onChange={(event) => onChange({ ...form, name: event.target.value })}
        />
        <Input
          min={0.01}
          placeholder="Base price"
          required
          step="0.01"
          type="number"
          value={form.base_price}
          onChange={(event) => onChange({ ...form, base_price: event.target.value })}
        />
        <select
          className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm text-ink"
          value={form.station}
          onChange={(event) => onChange({ ...form, station: event.target.value as Station })}
        >
          {Object.entries(STATION_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <Input
          placeholder="Description"
          value={form.description}
          onChange={(event) => onChange({ ...form, description: event.target.value })}
        />
        <Input
          placeholder="SKU"
          value={form.sku}
          onChange={(event) => onChange({ ...form, sku: event.target.value })}
        />
        <Input
          min={0}
          placeholder="Prep time in minutes"
          type="number"
          value={form.prep_time_minutes}
          onChange={(event) => onChange({ ...form, prep_time_minutes: event.target.value })}
        />
        <div className="rounded-xl border border-dashed border-line bg-appbg px-3 py-2 text-xs text-muted">
          Image upload integration can be connected to Cloudinary next.
        </div>
        <div className="sm:col-span-2 lg:col-span-4">
          <Button disabled={isBusy} type="submit">
            {isBusy ? 'Saving...' : 'Save menu item'}
          </Button>
        </div>
      </form>
    </div>
  )
}
