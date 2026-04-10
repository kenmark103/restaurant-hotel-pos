import { Link } from 'react-router-dom'
import { Button } from '@/shared/ui/Button'

export function NotFoundPage() {
  return (
    <section className="w-full rounded-3xl border border-line bg-white p-8 shadow-sm">
      <p className="app-label">Not found</p>
      <h1 className="mt-3 text-2xl font-semibold text-ink">This route does not exist.</h1>
      <p className="mt-3 text-sm leading-6 text-muted">Use the staff portal for internal operations or return to the guest-facing area.</p>
      <div className="mt-6">
        <Link to="/staff/login">
          <Button>Go to staff portal</Button>
        </Link>
      </div>
    </section>
  )
}
