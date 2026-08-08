interface ExhaustManifoldGlyphProps {
  className?: string
}

/** A lucide-style line glyph for the "Exhaust Manifold" category - no equivalent exists in the icon set. */
export function ExhaustManifoldGlyph({ className }: ExhaustManifoldGlyphProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M6 4h12" />
      <path d="M7 4c-1 4-1 6 1 9" />
      <path d="M10 4c0 4 0 6 1 9" />
      <path d="M14 4c-1 4-1 6 1 9" />
      <path d="M17 4c1 4 1 6-1 9" />
      <path d="M8 13h8l2 3-6 2-6-2 2-3Z" />
      <path d="M12 18v3" />
    </svg>
  )
}
