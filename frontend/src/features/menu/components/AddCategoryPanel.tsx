import type { FormEvent } from 'react'

import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'

export interface AddCategoryForm {
  name: string
  description: string
  display_order: string
}

interface AddCategoryPanelProps {
  form: AddCategoryForm
  isBusy: boolean
  onChange: (form: AddCategoryForm) => void
  onSubmit: (e: FormEvent) => void
  onClose: () => void
}

export function AddCategoryPanel({ form, isBusy, onChange, onSubmit, onClose }: AddCategoryPanelProps) {
  return (
    <div className="app-panel p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-ink">Create category</h2>
        <button
          type="button"
          className="rounded-lg border border-line px-2 py-1 text-xs font-semibold text-muted hover:text-ink"
          onClick={onClose}
        >
          Close
        </button>
      </div>
      <form className="mt-3 grid gap-3 sm:grid-cols-3" onSubmit={onSubmit}>
        <Input
          placeholder="Category name"
          required
          value={form.name}
          onChange={(event) => onChange({ ...form, name: event.target.value })}
        />
        <Input
          placeholder="Description"
          value={form.description}
          onChange={(event) => onChange({ ...form, description: event.target.value })}
        />
        <Input
          min={0}
          placeholder="Display order"
          type="number"
          value={form.display_order}
          onChange={(event) => onChange({ ...form, display_order: event.target.value })}
        />
        <div className="sm:col-span-3">
          <Button disabled={isBusy} type="submit">
            {isBusy ? 'Saving...' : 'Save category'}
          </Button>
        </div>
      </form>
    </div>
  )
}
