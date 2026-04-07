import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../lib/api'
import { useAuthStore } from '../lib/authStore'

export function StaffLoginPage() {
  const navigate = useNavigate()
  const setSession = useAuthStore((state) => state.setSession)
  const [email, setEmail] = useState('admin@example.com')
  const [password, setPassword] = useState('ChangeMe123!')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const response = await api.post('/auth/staff/login', { email, password })
      setSession({
        accessToken: response.data.access_token,
        refreshToken: response.data.refresh_token,
        audience: 'staff',
      })
      navigate('/staff/dashboard')
    } catch {
      setError('Staff login failed. Confirm the backend is running and migrations have been applied.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="mx-auto max-w-lg rounded-[2rem] bg-white/85 p-8 shadow-xl">
      <p className="text-sm uppercase tracking-[0.3em] text-ember">Staff access</p>
      <h1 className="mt-3 font-display text-4xl text-ink">Sign in to the internal console</h1>
      <p className="mt-3 text-sm text-ink/70">Accounts are provisioned internally. There is no public staff registration flow.</p>
      <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-ink">Email</span>
          <input
            className="w-full rounded-2xl border border-black/10 px-4 py-3"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            type="email"
          />
        </label>
        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-ink">Password</span>
          <input
            className="w-full rounded-2xl border border-black/10 px-4 py-3"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
          />
        </label>
        {error ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
        <button className="w-full rounded-full bg-ember px-5 py-3 font-semibold text-white" disabled={loading} type="submit">
          {loading ? 'Signing in...' : 'Sign in'}
        </button>
      </form>
    </section>
  )
}
