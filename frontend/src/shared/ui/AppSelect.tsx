import { SelectHTMLAttributes } from 'react'

type AppSelectProps = SelectHTMLAttributes<HTMLSelectElement>

export function AppSelect(props: AppSelectProps) {
  return (
    <select
      className="w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15"
      {...props}
    />
  )
}
