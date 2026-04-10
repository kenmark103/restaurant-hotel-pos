import { FormEvent, useState } from 'react'

import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'

type StaffLoginFormProps = {
  onSubmit: (payload: { email: string; password: string }) => Promise<void>
  isLoading: boolean
  error: string | null
  dark?: boolean
}

export function StaffLoginForm({ onSubmit, isLoading, error, dark = false }: StaffLoginFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await onSubmit({ email, password })
  }

  return (
    <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
      <label className="block">
        <span className={`mb-2 block text-sm font-semibold ${dark ? 'text-slate-200' : 'text-ink'}`}>Email</span>
        <Input value={email} onChange={(event) => setEmail(event.target.value)} type="email" autoComplete="username" />
      </label>
      <label className="block">
        <span className={`mb-2 block text-sm font-semibold ${dark ? 'text-slate-200' : 'text-ink'}`}>Password</span>
        <Input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" />
      </label>
      {error ? (
        <p className={`rounded-xl px-4 py-3 text-sm ${dark ? 'border border-danger/40 bg-danger/15 text-red-100' : 'border border-danger/20 bg-danger/5 text-danger'}`}>
          {error}
        </p>
      ) : null}
      <Button className="w-full" disabled={isLoading} type="submit">
        {isLoading ? 'Signing in...' : 'Sign in'}
      </Button>
    </form>
  )
}
