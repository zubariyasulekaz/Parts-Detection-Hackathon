import { Component, lazy, Suspense, useEffect, useRef, useState, type ReactNode } from 'react'

const HeroPart3D = lazy(() => import('./HeroPart3D'))

/**
 * Static stand-in with the rotor's silhouette - concentric machined rings and
 * a scan ring. Shown while the WebGL chunk downloads, and permanently on
 * hardware or browsers where it can't run, so the hero is never an empty hole.
 */
function RotorFallback() {
  return (
    <div aria-hidden="true" className="relative flex h-full w-full items-center justify-center">
      <div className="bg-spotlight-accent absolute h-64 w-64 rounded-full" />
      <div className="relative h-56 w-56 rounded-full border border-border-strong bg-linear-to-br from-surface-3 to-surface shadow-depth">
        <div className="absolute inset-6 rounded-full border border-border-strong bg-linear-to-tl from-surface-2 to-surface-3" />
        <div className="absolute inset-16 rounded-full border border-border-strong bg-surface-4" />
        <div className="absolute inset-[42%] rounded-full bg-background" />
        <div className="animate-pulse-soft absolute -inset-3 rounded-full border border-accent-2/40" />
      </div>
    </div>
  )
}

interface BoundaryProps {
  children: ReactNode
  fallback: ReactNode
}

/**
 * A missing WebGL context throws during render, and an uncaught throw here
 * would take the whole landing page down over a decoration. Class component
 * because error boundaries still have no hook equivalent in React 19.
 */
class CanvasBoundary extends Component<BoundaryProps, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

interface HeroPartStageProps {
  /**
   * Positioning and size for the stage. The caller owns `position` entirely -
   * this component deliberately sets none of its own, because a hardcoded
   * `relative` here silently beats a caller's `absolute` (same Tailwind layer,
   * source order decides, not class order) and drops the canvas back into
   * normal flow, where it pushes the hero copy down the page.
   */
  className?: string
}

/**
 * Owns everything about *whether* the 3D hero runs, keeping `HeroPart3D`
 * concerned only with what it looks like:
 *
 *  - lazy boundary, so three.js stays out of every other route's bundle
 *  - deferred mount until the stage is actually on screen, so the chunk isn't
 *    fetched and no GPU work starts for a visitor who never scrolls to it
 *  - error boundary for missing/blocked WebGL
 *  - reduced-motion pass-through, which stops the render loop but keeps the object
 */
export function HeroPartStage({ className = '' }: HeroPartStageProps) {
  const hostRef = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const host = hostRef.current
    if (!host) return
    if (typeof IntersectionObserver === 'undefined') {
      setVisible(true)
      return
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        // One-way: once mounted it stays mounted. Tearing the canvas down on
        // scroll-out would mean re-acquiring a WebGL context on every pass.
        if (entry.isIntersecting) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { rootMargin: '200px' },
    )
    observer.observe(host)
    return () => observer.disconnect()
  }, [])

  return (
    <div ref={hostRef} className={className}>
      {visible ? (
        <CanvasBoundary fallback={<RotorFallback />}>
          <Suspense fallback={<RotorFallback />}>
            <HeroPart3D still={prefersReducedMotion()} className="h-full w-full" />
          </Suspense>
        </CanvasBoundary>
      ) : (
        <RotorFallback />
      )}
    </div>
  )
}
