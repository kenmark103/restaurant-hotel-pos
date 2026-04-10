import { type FormEvent, useMemo, useState } from 'react'

import { ActivationLinkBox } from '@/features/staff/components/ActivationLinkBox'
import { InvitePanel, type InviteFormData } from '@/features/staff/components/InvitePanel'
import { StaffGroup } from '@/features/staff/components/StaffGroup'
import { useBranches } from '@/features/staff/hooks/useBranches'
import { useDisableStaff, useInviteStaff, useStaffList } from '@/features/staff/hooks/useStaff'
import { Spinner } from '@/shared/ui/Spinner'

const ROLES = ['admin', 'manager', 'cashier', 'server', 'kitchen'] as const
type Role = (typeof ROLES)[number]

const ROLE_DESCRIPTIONS: Record<Role, string> = {
  admin: 'Full access - branches, staff, reports',
  manager: 'Floor ops, menu, reports. No staff admin.',
  cashier: 'POS terminal + payments only',
  server: 'POS terminal, floor view',
  kitchen: 'KDS display only',
}

const BLANK_FORM: InviteFormData = {
  email: '',
  full_name: '',
  role: 'server',
  branch_id: '',
}

export function TeamPage() {
  const { data: branches } = useBranches()
  const { data: staff, isLoading } = useStaffList()
  const inviteMutation = useInviteStaff()
  const disableMutation = useDisableStaff()

  const [panelOpen, setPanelOpen] = useState(false)
  const [form, setForm] = useState<InviteFormData>(BLANK_FORM)
  const [inviteResult, setInviteResult] = useState<{ token: string; email: string } | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const grouped = useMemo(
    () => ({
      active: staff?.filter((member) => member.status === 'active') ?? [],
      invited: staff?.filter((member) => member.status === 'invited') ?? [],
      disabled: staff?.filter((member) => member.status === 'disabled') ?? [],
    }),
    [staff],
  )

  const handleInvite = async (event: FormEvent) => {
    event.preventDefault()
    setActionError(null)

    try {
      const result = await inviteMutation.mutateAsync({
        email: form.email.toLowerCase(),
        full_name: form.full_name,
        role: form.role as Role,
        branch_id: form.branch_id ? Number(form.branch_id) : null,
      })
      if (result.activation_token) {
        setInviteResult({ token: result.activation_token, email: form.email })
      } else {
        setInviteResult(null)
      }
      setForm(BLANK_FORM)
      setPanelOpen(false)
    } catch (error) {
      setActionError(getErrorMessage(error))
    }
  }

  const handleDisable = async (staffId: number) => {
    setActionError(null)
    try {
      await disableMutation.mutateAsync(staffId)
    } catch (error) {
      setActionError(getErrorMessage(error))
    }
  }

  if (isLoading) {
    return (
      <div className="app-panel p-8">
        <Spinner />
      </div>
    )
  }

  const origin = typeof window !== 'undefined' ? window.location.origin : ''

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="app-label">Team</p>
          <h2 className="mt-1 text-lg font-bold text-ink">{staff?.length ?? 0} staff members</h2>
        </div>
        <button
          type="button"
          className="btn-primary text-[12px]"
          onClick={() => {
            setPanelOpen((v) => !v)
            setInviteResult(null)
          }}
        >
          {panelOpen ? '× Cancel' : '+ Invite staff'}
        </button>
      </div>

      {inviteResult && (
        <ActivationLinkBox
          email={inviteResult.email}
          activationUrl={`${origin}/staff/activate?token=${inviteResult.token}`}
          onDismiss={() => setInviteResult(null)}
        />
      )}

      {panelOpen && (
        <InvitePanel
          branches={branches ?? []}
          roles={ROLES}
          roleDescriptions={ROLE_DESCRIPTIONS}
          form={form}
          isBusy={inviteMutation.isPending}
          actionError={actionError}
          onChange={setForm}
          onSubmit={(event) => void handleInvite(event)}
        />
      )}

      {!staff?.length ? (
        <div className="app-panel flex flex-col items-center py-16 text-center">
          <p className="text-base font-semibold text-ink">No staff yet</p>
          <p className="mt-1 text-sm text-muted">Invite your first team member above.</p>
        </div>
      ) : (
        <div className="space-y-4">
          <StaffGroup
            title="Active"
            members={grouped.active}
            tone="success"
            onDisable={handleDisable}
            isWorking={disableMutation.isPending}
          />
          <StaffGroup
            title="Invited - awaiting activation"
            members={grouped.invited}
            tone="warning"
            onDisable={handleDisable}
            isWorking={disableMutation.isPending}
          />
          {grouped.disabled.length > 0 && (
            <StaffGroup
              title="Disabled"
              members={grouped.disabled}
              tone="neutral"
              onDisable={handleDisable}
              isWorking={disableMutation.isPending}
            />
          )}
        </div>
      )}
    </div>
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
