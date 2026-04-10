import type { FormEvent } from 'react'

import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'

export interface InviteFormData {
  email: string
  full_name: string
  role: string
  branch_id: string
}

interface InvitePanelProps {
  branches: Array<{ id: number; name: string }>
  roles: readonly string[]
  roleDescriptions: Record<string, string>
  form: InviteFormData
  isBusy: boolean
  actionError: string | null
  onChange: (next: InviteFormData) => void
  onSubmit: (e: FormEvent) => void
}

export function InvitePanel({
  branches,
  roles,
  roleDescriptions,
  form,
  isBusy,
  actionError,
  onChange,
  onSubmit,
}: InvitePanelProps) {
  return (
    <div className="app-panel p-5">
      <p className="section-title mb-4">Invite a new staff member</p>
      <form className="space-y-4" onSubmit={onSubmit}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Input
            placeholder="Full name *"
            required
            value={form.full_name}
            onChange={(e) => onChange({ ...form, full_name: e.target.value })}
          />
          <Input
            placeholder="Email address *"
            required
            type="email"
            value={form.email}
            onChange={(e) => onChange({ ...form, email: e.target.value })}
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="label mb-1.5 block">Role</label>
            <select
              className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm text-ink"
              value={form.role}
              onChange={(e) => onChange({ ...form, role: e.target.value })}
            >
              {roles.map((role) => (
                <option key={role} value={role}>
                  {role.charAt(0).toUpperCase() + role.slice(1)}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-muted">{roleDescriptions[form.role]}</p>
          </div>

          <div>
            <label className="label mb-1.5 block">Branch (optional)</label>
            <select
              className="w-full rounded-xl border border-line bg-white px-3 py-2 text-sm text-ink"
              value={form.branch_id}
              onChange={(e) => onChange({ ...form, branch_id: e.target.value })}
            >
              <option value="">No branch (HQ / all access)</option>
              {branches.map((branch) => (
                <option key={branch.id} value={branch.id}>
                  {branch.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {actionError && <p className="text-xs text-danger">{actionError}</p>}

        <Button disabled={isBusy} type="submit">
          {isBusy ? 'Sending invite…' : 'Send invitation'}
        </Button>
      </form>
    </div>
  )
}
