import { useCallback, useRef, useState } from 'react'
import { Crop, X } from 'lucide-react'
import { MIN_CROP_FRACTION, regionArea, type CropRegion } from '@/utils/cropImage'

interface RefineSelectionProps {
  /** The photo as uploaded, at whatever size it is displayed. */
  imageUrl: string
  /** Called with the drawn region once the user is happy with it. */
  onSearchRegion: (region: CropRegion) => void
  onCancel: () => void
  busy?: boolean
}

/**
 * Draw a box around the part, and search only that.
 *
 * A customer photographs a part where it lies, so the product is often a small
 * fraction of the frame - a wheel chock under a trailer tyre, one connector
 * among five. The search describes the whole picture, so it answers about the
 * tyre.
 *
 * Measured on that exact case: searching the whole photo returned nothing like
 * a light; boxed to the one light, the top three results were all lights, with
 * a higher score than before.
 *
 * Offered rather than applied automatically, and only after a result the user
 * says is wrong. Automatic cropping was measured too and made good photos
 * worse - on a clean close-up of a water heater element it dropped the correct
 * products out of the top three. The customer is the only one who knows
 * whether their photo needs this.
 */
export function RefineSelection({ imageUrl, onSearchRegion, onCancel, busy }: RefineSelectionProps) {
  const frameRef = useRef<HTMLDivElement>(null)
  const startRef = useRef<{ x: number; y: number } | null>(null)
  const [region, setRegion] = useState<CropRegion | null>(null)

  /** Pointer position as a 0-1 fraction of the frame, clamped to its edges. */
  const pointAt = useCallback((event: React.PointerEvent) => {
    const frame = frameRef.current
    if (!frame) return null
    const box = frame.getBoundingClientRect()
    return {
      x: Math.min(1, Math.max(0, (event.clientX - box.left) / box.width)),
      y: Math.min(1, Math.max(0, (event.clientY - box.top) / box.height)),
    }
  }, [])

  const handleDown = useCallback((event: React.PointerEvent) => {
    if (busy) return
    const point = pointAt(event)
    if (!point) return
    // Capture on the frame so a drag that leaves the image still tracks, and
    // still ends - without this a pointer released outside never fires up.
    event.currentTarget.setPointerCapture(event.pointerId)
    startRef.current = point
    setRegion({ left: point.x, top: point.y, right: point.x, bottom: point.y })
  }, [busy, pointAt])

  const handleMove = useCallback((event: React.PointerEvent) => {
    const start = startRef.current
    if (!start) return
    const point = pointAt(event)
    if (!point) return
    // Normalised, so dragging up or left works the same as down or right.
    setRegion({
      left: Math.min(start.x, point.x),
      top: Math.min(start.y, point.y),
      right: Math.max(start.x, point.x),
      bottom: Math.max(start.y, point.y),
    })
  }, [pointAt])

  const handleUp = useCallback(() => {
    startRef.current = null
  }, [])

  const usable = region !== null && regionArea(region) >= MIN_CROP_FRACTION
  const percent = region ? Math.round(regionArea(region) * 100) : 0

  return (
    <div className="shadow-card rounded-xl border border-border bg-surface p-6">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="heading-eyebrow text-sm font-bold tracking-wide text-muted uppercase">
            Point at your part
          </h2>
          <p className="mt-1.5 max-w-prose text-sm text-muted">
            Drag a box around the part you want identified. Everything outside it is ignored,
            so a small part in a busy photo can be found.
          </p>
        </div>
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-muted transition-colors hover:text-foreground"
        >
          <X className="h-4 w-4" aria-hidden="true" />
          Cancel
        </button>
      </div>

      <div
        ref={frameRef}
        onPointerDown={handleDown}
        onPointerMove={handleMove}
        onPointerUp={handleUp}
        onPointerCancel={handleUp}
        className="relative mx-auto max-w-xl touch-none overflow-hidden rounded-lg border border-border-strong bg-surface-2 select-none"
        style={{ cursor: busy ? 'progress' : 'crosshair' }}
      >
        <img src={imageUrl} alt="Your photo" className="pointer-events-none block w-full" draggable={false} />
        {region && (
          <>
            {/* Dim everything outside the box, so the selection reads as the
                subject rather than as a rectangle drawn on top of it. */}
            <div
              className="pointer-events-none absolute inset-0 bg-black/55"
              style={{
                clipPath: `polygon(0% 0%, 0% 100%, ${region.left * 100}% 100%, ${region.left * 100}% ${region.top * 100}%, ${region.right * 100}% ${region.top * 100}%, ${region.right * 100}% ${region.bottom * 100}%, ${region.left * 100}% ${region.bottom * 100}%, ${region.left * 100}% 100%, 100% 100%, 100% 0%)`,
              }}
            />
            <div
              className="pointer-events-none absolute border-2 border-accent"
              style={{
                left: `${region.left * 100}%`,
                top: `${region.top * 100}%`,
                width: `${(region.right - region.left) * 100}%`,
                height: `${(region.bottom - region.top) * 100}%`,
              }}
            />
          </>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">
          {usable
            ? `Selected ${percent}% of the photo.`
            : 'Drag across the photo to select the part.'}
        </p>
        <button
          type="button"
          disabled={!usable || busy}
          onClick={() => region && onSearchRegion(region)}
          className="shadow-glow-accent inline-flex items-center gap-2 rounded-lg bg-linear-to-b from-accent-hover to-accent px-6 py-2.5 text-sm font-semibold text-white transition-transform hover:-translate-y-0.5 active:translate-y-0 disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
        >
          <Crop className="h-4 w-4" aria-hidden="true" />
          {busy ? 'Searching…' : 'Search this area'}
        </button>
      </div>
    </div>
  )
}
