import { useEffect, useRef, useState } from 'react'

/** Animates a number from 0 to `target` on mount/change - powers the "reveal" moment on confidence gauges. */
export function useCountUp(target: number, durationMs = 900): number {
  const [value, setValue] = useState(0)
  const frameRef = useRef(0)

  useEffect(() => {
    const prefersReducedMotion =
      typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (prefersReducedMotion) {
      setValue(target)
      return
    }

    let start: number | null = null
    setValue(0)

    function tick(timestamp: number) {
      if (start === null) start = timestamp
      const progress = Math.min((timestamp - start) / durationMs, 1)
      const eased = 1 - (1 - progress) ** 3
      setValue(target * eased)
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(tick)
      }
    }

    frameRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frameRef.current)
  }, [target, durationMs])

  return value
}
