import { Button } from '@/shared/ui/Button'

interface LineNoteModalProps {
  itemName: string
  note: string
  isBusy: boolean
  onChange: (note: string) => void
  onSave: () => void
  onClose: () => void
}

export function LineNoteModal({ itemName, note, isBusy, onChange, onSave, onClose }: LineNoteModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-4">
      <div className="w-full max-w-md rounded-2xl border border-line bg-white p-4 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="app-label">Ticket item note</p>
            <h2 className="text-base font-semibold text-ink">{itemName}</h2>
          </div>
          <button
            className="rounded-lg border border-line px-2 py-1 text-sm font-semibold text-muted hover:text-ink"
            disabled={isBusy}
            onClick={onClose}
            type="button"
          >
            Close
          </button>
        </div>

        <p className="mt-2 text-xs text-muted">Tip: press and hold a ticket line for 0.5s to open this editor.</p>
        <textarea
          className="mt-3 w-full rounded-xl border border-line bg-white px-3 py-2 text-sm text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10"
          placeholder="Examples: no onions, extra spicy, well done"
          rows={4}
          value={note}
          onChange={(event) => onChange(event.target.value)}
        />

        <div className="mt-3 flex items-center justify-end gap-2">
          <button
            className="rounded-xl border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-appbg"
            disabled={isBusy}
            onClick={onClose}
            type="button"
          >
            Cancel
          </button>
          <Button disabled={isBusy} onClick={onSave} type="button">
            {isBusy ? 'Saving...' : 'Save note'}
          </Button>
        </div>
      </div>
    </div>
  )
}
