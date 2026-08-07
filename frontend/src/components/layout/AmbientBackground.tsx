interface AmbientBackgroundProps {
  variant?: 'accent' | 'success'
  className?: string
}

/**
 * Layered page-background: a masked dot-grid "sky", a 3D-tilted CSS
 * perspective grid "floor" meeting it at a horizon, ambient glow at two
 * depths, and a soft vignette. Pure CSS (real 3D transforms, no
 * canvas/particle library) — the dimensional, precision-instrument
 * backdrop for hero-type moments. Drop into a `relative overflow-hidden`
 * container. Purely decorative — never carries content or state.
 */
export function AmbientBackground({ variant = 'accent', className = '' }: AmbientBackgroundProps) {
  const spotlightClass = variant === 'success' ? 'bg-spotlight-success' : 'bg-spotlight-accent'

  return (
    <div aria-hidden="true" className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}>
      {/* sky: provided by the page-level star-field (body::before) showing
          through — this layer stopped painting its own dot grid so the
          stars never double up or slide against each other on scroll */}

      {/* horizon glow, breathing gently */}
      <div className={`animate-glow-pulse absolute top-[38%] left-1/2 h-105 w-205 -translate-x-1/2 ${spotlightClass}`} />
      {/* nearer, sharper depth cue */}
      <div className="bg-spotlight-accent absolute right-[12%] bottom-[6%] h-55 w-80 opacity-70" />
      {/* nebula counterweight on the opposite flank */}
      <div className="bg-spotlight-nebula absolute bottom-[18%] left-[6%] h-60 w-90 opacity-80" />

      {/* floor, receding to the horizon */}
      <div className="mask-[linear-gradient(to_top,black_55%,transparent)] absolute inset-x-0 bottom-0 h-[46%] overflow-hidden">
        <div className="bg-perspective-grid mask-[linear-gradient(to_bottom,transparent,black_55%)] absolute inset-x-[-25%] bottom-0 h-full" />
      </div>

      {/* vignette for cinematic falloff at the edges — eased so the page
          atmosphere still glows through instead of clamping back to black */}
      <div className="absolute inset-0 opacity-80 [background:radial-gradient(ellipse_at_50%_35%,transparent_52%,var(--color-background)_100%)]" />
    </div>
  )
}
