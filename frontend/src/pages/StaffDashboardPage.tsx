import { useAuthStore } from '../lib/authStore'

export function StaffDashboardPage() {
  const clearSession = useAuthStore((state) => state.clearSession)

  return (
    <section className="rounded-[2rem] bg-white/80 p-8 shadow-xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.3em] text-moss">Staff dashboard</p>
          <h1 className="mt-3 font-display text-4xl text-ink">Operations workspace</h1>
          <p className="mt-3 max-w-2xl text-ink/70">
            This authenticated route is where POS terminals, menu management, and operational controls will expand next.
          </p>
        </div>
        <button className="rounded-full border border-black/10 px-4 py-2 text-sm font-semibold" onClick={clearSession}>
          Clear session
        </button>
      </div>
    </section>
  )
}
