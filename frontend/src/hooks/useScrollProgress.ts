import { useEffect, useRef } from 'react'

interface ScrollProgressOptions {
  /**
   * Fraction of the remaining distance closed each frame. Lower is heavier.
   * 0.12 trails the scrollbar by ~150ms, which is what makes the motion read
   * as inertial rather than welded to the wheel.
   */
  smoothing?: number
  disabled?: boolean
}

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/**
 * Reports 0..1 for how far a section has travelled through the viewport, eased.
 *
 * Delivered through a callback rather than as state on purpose: this fires every
 * frame while scrolling, and a `setState` at that rate would re-render the whole
 * subtree ~60x/second. Callers write the continuous values (path offset,
 * transforms) straight to the DOM and keep React state for the things that
 * actually change rarely, like which step is lit.
 *
 * The value maps the reader's eye line onto the section: 0 when the section's
 * top reaches 55% of the viewport height, 1 when its bottom does. Anything
 * driven by this therefore sits at screen centre for the whole scroll.
 *
 * An earlier version spread the range over the section *plus* a viewport
 * height, which sounds equivalent and is not: on a section taller than the
 * screen the animation fell progressively further behind the reader, so by
 * mid-page every card on screen was still dormant and the pulse was somewhere
 * above the fold. Tie it to the centre line and the lit/unlit boundary is
 * always exactly where the reader is looking.
 *
 * Under reduced motion it reports 1 once and attaches nothing: the whole diagram
 * renders in its final, complete state.
 */
export function useScrollProgress<T extends HTMLElement>(
  onProgress: (progress: number) => void,
  { smoothing = 0.12, disabled = false }: ScrollProgressOptions = {},
) {
  const ref = useRef<T>(null)
  const callbackRef = useRef(onProgress)
  callbackRef.current = onProgress

  useEffect(() => {
    const node = ref.current
    if (!node) return

    if (disabled || prefersReducedMotion()) {
      callbackRef.current(1)
      return
    }

    let frame = 0
    let current = 0
    let target = 0
    let running = false

    const measure = () => {
      const rect = node.getBoundingClientRect()
      // Slightly below true centre: the stage being read should already be lit,
      // not lighting up as it crosses the midpoint.
      const eyeLine = window.innerHeight * 0.55
      target = rect.height <= 0 ? 0 : Math.min(Math.max((eyeLine - rect.top) / rect.height, 0), 1)
    }

    const tick = () => {
      current += (target - current) * smoothing
      // Settle and stop rather than idling a rAF loop forever - otherwise the
      // page keeps a frame callback alive for as long as it is open.
      if (Math.abs(target - current) < 0.0005) {
        current = target
        running = false
        frame = 0
        callbackRef.current(current)
        return
      }
      callbackRef.current(current)
      frame = window.requestAnimationFrame(tick)
    }

    const schedule = () => {
      measure()
      if (!running) {
        running = true
        frame = window.requestAnimationFrame(tick)
      }
    }

    // Land on the correct value for the current scroll position without
    // animating up to it - a reader arriving mid-page shouldn't watch the
    // pipeline replay from zero.
    measure()
    current = target
    callbackRef.current(current)

    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)
    return () => {
      if (frame !== 0) window.cancelAnimationFrame(frame)
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
    }
  }, [disabled, smoothing])

  return ref
}
