export function Spinner() {
  return (
    <div className="flex items-center gap-3 text-ink">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" />
      <span className="text-sm font-medium text-muted">Loading...</span>
    </div>
  )
}
