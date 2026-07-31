interface ShockAbsorberGlyphProps {
  className?: string
}

/** A lucide-style line glyph for the "Shock Absorbers" category — a coil-over strut. */
export function ShockAbsorberGlyph({ className }: ShockAbsorberGlyphProps) {
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
      <path d="M9 3h6" />
      <path d="M12 3v3.4" />
      <path d="M8 6.4c0 .8 1.8 1.4 4 1.4s4-.6 4-1.4" />
      <path d="M8 9.4c0 .8 1.8 1.4 4 1.4s4-.6 4-1.4" />
      <path d="M8 12.4c0 .8 1.8 1.4 4 1.4s4-.6 4-1.4" />
      <path d="M12 13.8V16" />
      <rect x="10" y="16" width="4" height="5" rx="1" />
      <path d="M9 21h6" />
    </svg>
  )
}
