import { ButtonHTMLAttributes } from 'react'

type CustomerLoginButtonProps = ButtonHTMLAttributes<HTMLAnchorElement> & {
  enabled: boolean
  href: string
}

export function CustomerLoginButton({ enabled, href, ...props }: CustomerLoginButtonProps) {
  return (
    <a
      className={`mt-4 inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold text-white ${
        enabled ? 'bg-ink hover:bg-slate' : 'pointer-events-none bg-slate/40'
      }`}
      href={href}
      {...props}
    >
      Continue with Google
    </a>
  )
}
