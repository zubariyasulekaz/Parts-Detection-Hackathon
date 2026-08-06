import { useEffect, useState } from 'react'

/** Long enough to read the caption, short enough that the hero never looks static. */
export const DEFAULT_ROTATION_MS = 3200

interface RotatingIndexOptions {
  /** Stops the timer without losing the current index — e.g. once the user has their own image up. */
  paused?: boolean
  intervalMs?: number
}

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/**
 * Cycles 0..count-1 on a timer, and exposes a setter so the same state can be
 * driven manually (dot controls) as well.
 *
 * Readers who asked for reduced motion get a still frame rather than a slower
 * carousel — the rotation is decoration, and CSS alone can't stop a JS timer.
 */
export function useRotatingIndex(
  count: number,
  { paused = false, intervalMs = DEFAULT_ROTATION_MS }: RotatingIndexOptions = {},
): [number, (index: number) => void] {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (paused || count < 2 || prefersReducedMotion()) return
    const timer = window.setInterval(() => {
      setIndex((current) => (current + 1) % count)
    }, intervalMs)
    return () => window.clearInterval(timer)
  }, [count, intervalMs, paused])

  // Guard the modulo: callers must call this hook before any early return, so
  // count can legitimately be 0 and `index % 0` would hand back NaN.
  return [count > 0 ? index % count : 0, setIndex]
}
