import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { api } from '../lib/api'
import { useAuthStore } from '../lib/authStore'

type GoogleStartResponse = {
  enabled: boolean
  authorization_url: string | null
  message: string
}

export function CustomerLoginPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const setSession = useAuthStore((state) => state.setSession)
  const [googleState, setGoogleState] = useState<GoogleStartResponse | null>(null)

  useEffect(() => {
    const accessToken = searchParams.get('access_token')
    const refreshToken = searchParams.get('refresh_token')
    if (accessToken && refreshToken) {
      setSession({ accessToken, refreshToken, audience: 'customer' })
      navigate('/account/overview', { replace: true })
    }
  }, [navigate, searchParams, setSession])

  useEffect(() => {
    api
      .post<GoogleStartResponse>('/auth/customers/google/start')
      .then((response) => setGoogleState(response.data))
      .catch(() =>
        setGoogleState({
          enabled: false,
          authorization_url: null,
          message: 'Unable to reach the backend right now.',
        }),
      )
  }, [])

  return (
    <section className="mx-auto max-w-2xl rounded-[2rem] bg-white/85 p-8 shadow-xl">
      <p className="text-sm uppercase tracking-[0.3em] text-moss">Customer account</p>
      <h1 className="mt-3 font-display text-4xl text-ink">Reservations and loyalty access</h1>
      <p className="mt-3 max-w-xl text-ink/70">
        Customers can use Google to access reservation history, preferences, and future loyalty features.
      </p>
      <div className="mt-8 rounded-[1.5rem] bg-sand p-6">
        <p className="text-sm text-ink/80">{googleState?.message ?? 'Loading Google sign-in status...'}</p>
        <a
          className={`mt-4 inline-flex rounded-full px-5 py-3 font-semibold text-white ${
            googleState?.enabled ? 'bg-moss' : 'pointer-events-none bg-moss/40'
          }`}
          href={googleState?.authorization_url ?? '#'}
        >
          Continue with Google
        </a>
      </div>
    </section>
  )
}
