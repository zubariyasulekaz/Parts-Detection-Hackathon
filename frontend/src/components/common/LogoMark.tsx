interface LogoMarkProps {
  className?: string
}

export function LogoMark({ className = 'h-8 w-8' }: LogoMarkProps) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#141A21" />
      <path d="M16 6L25 11V21L16 26L7 21V11L16 6Z" stroke="#2F80ED" strokeWidth="2" strokeLinejoin="round" fill="none" />
      <circle cx="16" cy="16" r="3.4" fill="#2F80ED" />
    </svg>
  )
}
