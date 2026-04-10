import { type FormEvent, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { useActivateStaff } from '@/features/staff/hooks/useStaff'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'

export function StaffActivatePage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token') ?? ''
  const activateMutation = useActivateStaff()

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-appbg">
        <div className="text-center">
          <p className="text-sm font-semibold text-danger">Invalid activation link</p>
          <p className="mt-1 text-xs text-muted">Contact your manager for a new invitation.</p>
        </div>
      </div>
    )
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)

    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }

    try {
      await activateMutation.mutateAsync({ token, password })
      setDone(true)
      setTimeout(() => navigate('/staff/login', { replace: true }), 2500)
    } catch (submitError: unknown) {
      const message =
        (submitError as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Activation failed. The link may have expired.'
      setError(message)
    }
  }

  if (done) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-appbg">
        <div className="text-center">
          <p className="text-2xl">?</p>
          <p className="mt-2 text-sm font-semibold text-success-text">Account activated</p>
          <p className="mt-1 text-xs text-muted">Redirecting you to login…</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-appbg px-4">
      <div className="w-full max-w-sm rounded-2xl border border-line bg-white p-6 shadow-sm">
        <p className="app-label">Staff activation</p>
        <h1 className="mt-1 text-xl font-bold text-ink">Set your password</h1>
        <p className="mt-1 text-sm text-muted">Choose a secure password to activate your account.</p>

        <form className="mt-5 space-y-3" onSubmit={(event) => void handleSubmit(event)}>
          <Input
            placeholder="New password (min 8 chars)"
            required
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <Input
            placeholder="Confirm password"
            required
            type="password"
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
          />
          {error && <p className="text-xs text-danger">{error}</p>}
          <Button className="w-full" disabled={activateMutation.isPending} type="submit">
            {activateMutation.isPending ? 'Activating…' : 'Activate account'}
          </Button>
        </form>
      </div>
    </div>
  )
}
