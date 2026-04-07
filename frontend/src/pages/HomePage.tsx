export function HomePage() {
  return (
    <section className="grid gap-8 lg:grid-cols-[1.4fr_1fr]">
      <div className="rounded-[2rem] bg-ink px-8 py-10 text-sand shadow-2xl">
        <p className="mb-4 text-sm uppercase tracking-[0.4em] text-sand/70">Shift 0 baseline</p>
        <h1 className="font-display text-5xl leading-tight">Run restaurant operations now, expand into hospitality next.</h1>
        <p className="mt-6 max-w-2xl text-lg text-sand/80">
          This baseline includes Dockerized frontend and backend services, internal staff auth, and customer Google OAuth
          entry points for reservations and loyalty.
        </p>
      </div>
      <div className="space-y-4 rounded-[2rem] bg-white/75 p-8 shadow-xl">
        <h2 className="font-display text-3xl text-ink">Current slices</h2>
        <ul className="space-y-3 text-sm text-ink/80">
          <li>Staff login flow with admin-created accounts only.</li>
          <li>Customer account area prepared for Google OAuth.</li>
          <li>FastAPI + Postgres + Redis + Vite local development stack.</li>
        </ul>
      </div>
    </section>
  )
}
