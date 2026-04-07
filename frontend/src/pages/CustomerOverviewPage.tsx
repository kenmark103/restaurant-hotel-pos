import { useAuthStore } from '../lib/authStore'

export function CustomerOverviewPage() {
  const clearSession = useAuthStore((state) => state.clearSession)

  return (
    <section className="rounded-[2rem] bg-white/80 p-8 shadow-xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.3em] text-moss">Customer overview</p>
          <h1 className="mt-3 font-display text-4xl text-ink">Reservations and loyalty home</h1>
          <p className="mt-3 max-w-2xl text-ink/70">
            This area will grow into bookings, saved preferences, visit history, and loyalty balances once the next shifts land.
          </p>
        </div>
        <button className="rounded-full border border-black/10 px-4 py-2 text-sm font-semibold" onClick={clearSession}>
          Clear session
        </button>
      </div>
    </section>
  )
}
