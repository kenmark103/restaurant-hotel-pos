import { PropsWithChildren, ReactNode } from 'react'

interface SectionCardProps extends PropsWithChildren {
  title?: string
  eyebrow?: string
  description?: string
  actions?: ReactNode
  muted?: boolean
  className?: string
}

export function SectionCard({ title, eyebrow, description, actions, muted = false, className = '', children }: SectionCardProps) {
  return (
    <section className={`${muted ? 'app-panel-muted' : 'app-panel'} p-5 ${className}`.trim()}>
      {(eyebrow || title || description || actions) ? (
        <div className="mb-5 flex flex-col gap-3 border-b border-line pb-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-2xl">
            {eyebrow ? <p className="app-label">{eyebrow}</p> : null}
            {title ? <h2 className="mt-2 text-lg font-semibold text-ink">{title}</h2> : null}
            {description ? <p className="mt-2 text-sm leading-6 text-muted">{description}</p> : null}
          </div>
          {actions ? <div className="flex shrink-0 items-center gap-3">{actions}</div> : null}
        </div>
      ) : null}
      {children}
    </section>
  )
}
