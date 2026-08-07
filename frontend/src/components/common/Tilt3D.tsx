import { useTilt } from '@/hooks/useTilt'
import type { ReactNode } from 'react'

/**
 * Named presets rather than raw degrees at every call site, so "how 3D is
 * this page" stays one decision instead of forty. `subtle` is for anything
 * appearing in a grid of many; `strong` is reserved for single hero objects,
 * where a big angle has room to breathe.
 */
const INTENSITY = {
  subtle: { maxTiltDeg: 5, liftPx: 8, scale: 1.01 },
  normal: { maxTiltDeg: 9, liftPx: 16, scale: 1.02 },
  strong: { maxTiltDeg: 14, liftPx: 26, scale: 1.03 },
} as const

interface Tilt3DProps {
  children: ReactNode
  /** Classes for the tilting surface itself - borders, background, radius. */
  className?: string
  /** Classes for the perspective parent. Rarely needed; use for layout/sizing. */
  sceneClassName?: string
  intensity?: keyof typeof INTENSITY
  /** Shallower camera, for tiles too small to show a 1200px perspective. */
  near?: boolean
  /** Pointer-tracking specular sweep. Worth it on cards ~200px and up. */
  glare?: boolean
  disabled?: boolean
  onClick?: () => void
}

/**
 * Wraps content in a perspective scene plus a pointer-tilted surface - the two
 * halves the CSS needs in order to rotate rather than shear.
 *
 * The glare is rendered here rather than left to callers because it has to be
 * the last child, inset, and non-interactive; getting any of those wrong makes
 * it swallow clicks on the card underneath it.
 *
 * Degrades to a plain nested div under reduced motion or on touch - `useTilt`
 * declines to attach, the custom properties stay unset, and `tilt-3d` collapses
 * to the identity transform.
 */
export function Tilt3D({
  children,
  className = '',
  sceneClassName = '',
  intensity = 'normal',
  near = false,
  glare = false,
  disabled = false,
  onClick,
}: Tilt3DProps) {
  const ref = useTilt<HTMLDivElement>({ ...INTENSITY[intensity], glare, disabled })
  const scene = near ? 'perspective-scene-near' : 'perspective-scene'

  return (
    <div className={`${scene} ${sceneClassName}`}>
      <div ref={ref} onClick={onClick} className={`tilt-3d relative ${className}`}>
        {children}
        {glare && (
          <span
            aria-hidden="true"
            className="tilt-glare pointer-events-none absolute inset-0 rounded-[inherit]"
          />
        )}
      </div>
    </div>
  )
}
