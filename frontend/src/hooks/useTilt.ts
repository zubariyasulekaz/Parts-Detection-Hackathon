import { useEffect, useRef } from 'react'

/**
 * Past roughly 10° a card stops reading as a surface catching light and
 * starts reading as a novelty toy. Small tiles get less, not more.
 */
export const MAX_TILT_DEG = 9
/** How far the surface rises toward the camera while pointed at. */
export const TILT_LIFT_PX = 16
export const TILT_SCALE = 1.02

interface TiltOptions {
  maxTiltDeg?: number
  liftPx?: number
  scale?: number
  /**
   * Also drive `--glare-x` / `--glare-y` / `--glare-opacity` for a child
   * carrying the `tilt-glare` utility. Off by default: the highlight costs
   * a compositor layer, and it only pays off on surfaces big enough to see it.
   */
  glare?: boolean
  disabled?: boolean
}

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/**
 * Touch and pen have no hover state, so a tilt could only ever fire mid-tap -
 * it reads as a rendering glitch rather than an effect. Phones also pay the
 * most for the extra compositing, so they opt out entirely.
 */
function isCoarsePointer(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(pointer: coarse)').matches
}

/**
 * Pointer-driven 3D tilt. Returns a ref for the element carrying the `tilt-3d`
 * utility; the element's parent must carry `perspective-scene` or the rotation
 * is orthographic and just looks sheared.
 *
 * Writes CSS custom properties straight onto the node rather than going through
 * React state - a pointermove-rate `setState` would re-render the whole card
 * subtree ~120x/second for what is purely a visual transform. Updates are
 * coalesced into one rAF frame, and the element rect is cached on enter (then
 * refreshed on scroll/resize) so the move handler never forces a layout.
 *
 * Direction: the edge nearest the pointer tilts *away*, as though the cursor
 * were pressing into the surface, with the glare brightening under it.
 */
export function useTilt<T extends HTMLElement = HTMLDivElement>({
  maxTiltDeg = MAX_TILT_DEG,
  liftPx = TILT_LIFT_PX,
  scale = TILT_SCALE,
  glare = false,
  disabled = false,
}: TiltOptions = {}) {
  const ref = useRef<T>(null)

  useEffect(() => {
    const node = ref.current
    if (!node || disabled || prefersReducedMotion() || isCoarsePointer()) return

    let rect: DOMRect | null = null
    let frame = 0
    let pending: { x: number; y: number } | null = null

    const measure = () => {
      rect = node.getBoundingClientRect()
    }

    const apply = () => {
      frame = 0
      if (!pending || !rect || rect.width === 0 || rect.height === 0) return
      // Pointer position as a 0..1 fraction of the element, clamped so a
      // pointermove that lands a pixel outside during fast travel can't fling
      // the card past its maximum angle.
      const px = Math.min(Math.max((pending.x - rect.left) / rect.width, 0), 1)
      const py = Math.min(Math.max((pending.y - rect.top) / rect.height, 0), 1)

      node.style.setProperty('--tilt-x', `${(0.5 - py) * 2 * maxTiltDeg}deg`)
      node.style.setProperty('--tilt-y', `${(px - 0.5) * 2 * maxTiltDeg}deg`)

      if (glare) {
        node.style.setProperty('--glare-x', `${px * 100}%`)
        node.style.setProperty('--glare-y', `${py * 100}%`)
      }
    }

    const schedule = () => {
      if (frame === 0) frame = window.requestAnimationFrame(apply)
    }

    const handleEnter = (event: PointerEvent) => {
      measure()
      pending = { x: event.clientX, y: event.clientY }
      node.dataset.tilting = 'true'
      node.style.setProperty('--tilt-lift', `${liftPx}px`)
      node.style.setProperty('--tilt-scale', `${scale}`)
      if (glare) node.style.setProperty('--glare-opacity', '1')
      schedule()
    }

    const handleMove = (event: PointerEvent) => {
      pending = { x: event.clientX, y: event.clientY }
      schedule()
    }

    const handleLeave = () => {
      if (frame !== 0) {
        window.cancelAnimationFrame(frame)
        frame = 0
      }
      pending = null
      // Drop data-tilting first so the long spring transition - not the 120ms
      // tracking one - governs the settle back to flat.
      delete node.dataset.tilting
      node.style.setProperty('--tilt-x', '0deg')
      node.style.setProperty('--tilt-y', '0deg')
      node.style.setProperty('--tilt-lift', '0px')
      node.style.setProperty('--tilt-scale', '1')
      if (glare) node.style.setProperty('--glare-opacity', '0')
    }

    node.addEventListener('pointerenter', handleEnter)
    node.addEventListener('pointermove', handleMove)
    node.addEventListener('pointerleave', handleLeave)
    // A card hovered while the page scrolls under it would otherwise keep
    // using the rect from wherever it was when the pointer arrived.
    window.addEventListener('scroll', measure, { passive: true })
    window.addEventListener('resize', measure)

    return () => {
      if (frame !== 0) window.cancelAnimationFrame(frame)
      node.removeEventListener('pointerenter', handleEnter)
      node.removeEventListener('pointermove', handleMove)
      node.removeEventListener('pointerleave', handleLeave)
      window.removeEventListener('scroll', measure)
      window.removeEventListener('resize', measure)
    }
  }, [disabled, glare, liftPx, maxTiltDeg, scale])

  return ref
}
