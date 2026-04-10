import { FormEvent, useState } from 'react'

import { useBranches, useCreateBranch } from '@/features/staff/hooks/useBranches'
import { Spinner } from '@/shared/ui/Spinner'
import { Input } from '@/shared/ui/Input'
import { Button } from '@/shared/ui/Button'

export function BranchesPage() {
  const { data, isLoading } = useBranches()
  const createMutation = useCreateBranch()
  const [panelOpen, setPanelOpen] = useState(false)
  const [form, setForm] = useState({
    name: '', code: '', address: '', phone: '', timezone: 'Africa/Nairobi',
  })

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    await createMutation.mutateAsync({
      ...form,
      address: form.address || null,
      phone: form.phone || null,
      code: form.code.toUpperCase(),
    })
    setForm({ name: '', code: '', address: '', phone: '', timezone: 'Africa/Nairobi' })
    setPanelOpen(false)
  }

  if (isLoading) return <Spinner />

  return (
    <div className="space-y-4">

      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div>
          <p className="label">Branches</p>
          <h2 className="mt-1 text-lg font-bold text-ink">
            Operating locations — {data?.length ?? 0} registered
          </h2>
        </div>
        <button className="btn-primary text-[12px]" onClick={() => setPanelOpen((v) => !v)}>
          {panelOpen ? '✕ Cancel' : '+ New branch'}
        </button>
      </div>

      {/* Create panel */}
      {panelOpen && (
        <div className="card p-5">
          <p className="section-title mb-4">Create a new location</p>
          <form className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" onSubmit={handleSubmit}>
            <Input placeholder="Branch name *" required value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
            <Input placeholder="Code (e.g. NBI-01) *" required value={form.code}
              onChange={(e) => setForm((f) => ({ ...f, code: e.target.value.toUpperCase() }))} />
            <Input placeholder="Phone" value={form.phone}
              onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} />
            <Input placeholder="Address" value={form.address}
              onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))} />
            <Input placeholder="Timezone" value={form.timezone}
              onChange={(e) => setForm((f) => ({ ...f, timezone: e.target.value }))} />
            <div className="flex items-end">
              <Button disabled={createMutation.isPending} type="submit" className="w-full">
                {createMutation.isPending ? 'Creating…' : 'Create branch'}
              </Button>
            </div>
            {createMutation.isError && (
              <p className="sm:col-span-2 lg:col-span-3 text-[12px] text-danger">Could not create this branch.</p>
            )}
          </form>
        </div>
      )}

      {/* Branches list */}
      {!data?.length ? (
        <div className="card flex flex-col items-center py-16 text-center">
          <span className="text-4xl opacity-30">🏠</span>
          <p className="mt-3 text-[14px] font-semibold text-ink">No branches yet</p>
          <p className="mt-1 text-[12px] text-muted">
            Create your first location to start assigning staff, tables, and menus.
          </p>
          <button className="btn-primary mt-5" onClick={() => setPanelOpen(true)}>
            Create first branch
          </button>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((branch) => (
            <div key={branch.id} className="card p-4">
              <div className="flex items-start justify-between gap-2">
                <p className="text-[14px] font-bold text-ink">{branch.name}</p>
                <span className="rounded-pill bg-appbg px-2 py-0.5 font-mono text-[10px] font-medium text-muted border border-line">
                  {branch.code}
                </span>
              </div>
              <p className="mt-1.5 text-[12px] text-muted">{branch.address ?? 'No address provided'}</p>
              <div className="mt-3 flex items-center gap-3 text-[11px] text-faint">
                {branch.phone && <span>📞 {branch.phone}</span>}
                <span className="font-mono">{branch.timezone}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}