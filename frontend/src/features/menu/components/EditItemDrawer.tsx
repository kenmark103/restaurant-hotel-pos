import type { FormEvent } from 'react'

import type { MenuItemWithCategory, Station } from '@/features/menu/types'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'

export interface EditItemForm {
  name: string
  description: string
  base_price: string
  prep_time_minutes: string
  station: Station
  sku: string
  image_url: string
  is_available: boolean
}

interface EditItemDrawerProps {
  item: MenuItemWithCategory
  form: EditItemForm
  isBusy: boolean
  onChange: (value: EditItemForm) => void
  onClose: () => void
  onSubmit: (event: FormEvent) => Promise<void>
}

const STATION_LABELS: Record<Station, string> = {
  any: 'Any',
  grill: 'Grill',
  fryer: 'Fryer',
  bar: 'Bar',
  cold: 'Cold',
  pass: 'Pass',
}

export function EditItemDrawer({ item, form, isBusy, onChange, onClose, onSubmit }: EditItemDrawerProps) {
  return (
    <div className="fixed inset-0 z-50 flex bg-slate-950/40">
      <div className="flex-1" onClick={onClose} />
      <aside className="flex h-full w-full max-w-md flex-col border-l border-line bg-white p-4 shadow-2xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="app-label">Edit item</p>
            <h2 className="text-lg font-semibold text-ink">{item.name}</h2>
          </div>
          <button
            className="rounded-lg border border-line px-3 py-1.5 text-sm font-semibold text-muted hover:text-ink"
            disabled={isBusy}
            onClick={onClose}
            type="button"
          >
            Close
          </button>
        </div>

        <form className="mt-4 flex min-h-0 flex-1 flex-col gap-3" onSubmit={(event) => void onSubmit(event)}>
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
          <Input
            min={0}
            placeholder="Prep time in minutes"
            type="number"
            value={form.prep_time_minutes}
            onChange={(event) => onChange({ ...form, prep_time_minutes: event.target.value })}
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
            placeholder="Image URL"
            value={form.image_url}
            onChange={(event) => onChange({ ...form, image_url: event.target.value })}
          />
          <label className="inline-flex items-center gap-2 text-sm text-ink">
            <input
              checked={form.is_available}
              className="h-4 w-4"
              onChange={(event) => onChange({ ...form, is_available: event.target.checked })}
              type="checkbox"
            />
            Item available for sale
          </label>

          <div className="mt-auto flex items-center justify-end gap-2 pt-2">
            <button
              className="rounded-xl border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-appbg"
              disabled={isBusy}
              onClick={onClose}
              type="button"
            >
              Cancel
            </button>
            <Button disabled={isBusy} type="submit">
              {isBusy ? 'Saving...' : 'Save changes'}
            </Button>
          </div>
        </form>
      </aside>
    </div>
  )
}
