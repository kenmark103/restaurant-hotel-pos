interface ActivationLinkBoxProps {
  email: string
  activationUrl: string
  onDismiss: () => void
}

export function ActivationLinkBox({ email, activationUrl, onDismiss }: ActivationLinkBoxProps) {
  return (
    <div className="rounded-xl border border-success/30 bg-success/5 p-4">
      <p className="text-sm font-semibold text-success-text">Invitation created for {email}</p>
      <p className="mt-1 text-xs text-muted">Share this activation link with the staff member. It expires in 72 hours.</p>
      <div className="mt-2 flex items-center gap-2 rounded-lg border border-line bg-white p-2 font-mono text-xs text-ink">
        <span className="flex-1 break-all">{activationUrl}</span>
        <button
          type="button"
          className="shrink-0 rounded-lg border border-line px-2 py-1 text-xs text-muted hover:text-ink"
          onClick={() => void navigator.clipboard.writeText(activationUrl)}
        >
          Copy
        </button>
      </div>
      <button type="button" className="mt-2 text-xs text-muted hover:text-ink" onClick={onDismiss}>
        Dismiss
      </button>
    </div>
  )
}
