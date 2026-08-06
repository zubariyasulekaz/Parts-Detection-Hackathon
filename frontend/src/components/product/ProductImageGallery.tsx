import { useState } from 'react'
import { PartIllustration } from '@/components/common/PartIllustration'
import { useRotatingIndex } from '@/hooks/useRotatingIndex'
import { isDisplayableImageUrl } from '@/utils/format'

interface ProductImageGalleryProps {
  category: string
  images: string[]
}

/** Slower than the landing-page carousel: this one sits beside text being read. */
const GALLERY_ROTATION_MS = 4000

export function ProductImageGallery({ category, images }: ProductImageGalleryProps) {
  const displayable = images.filter(isDisplayableImageUrl)
  // Picking a thumbnail is a deliberate "show me this one", so rotation stops
  // for good rather than yanking the photo away a few seconds later.
  const [pinned, setPinned] = useState(false)
  const [activeIndex, setActiveIndex] = useRotatingIndex(displayable.length, {
    paused: pinned,
    intervalMs: GALLERY_ROTATION_MS,
  })

  if (displayable.length === 0) {
    return <PartIllustration category={category} className="aspect-square w-full rounded-xl" />
  }

  function pin(index: number) {
    setPinned(true)
    setActiveIndex(index)
  }

  return (
    <div className="flex flex-col gap-3">
      {/* min-h-0 so a portrait photo cannot override the square ratio via this
          flex item's automatic minimum height. */}
      <div className="relative aspect-square min-h-0 overflow-hidden rounded-xl border border-border-strong bg-surface-2">
        {/* All frames stay mounted and cross-fade, so rotation never flashes a
            blank box while the next photo loads. */}
        {displayable.map((src, index) => (
          <img
            key={src}
            src={src}
            alt={index === activeIndex ? `${category} photo ${index + 1} of ${displayable.length}` : ''}
            aria-hidden={index !== activeIndex}
            className={`absolute inset-0 h-full w-full object-contain transition-opacity duration-500 ${
              index === activeIndex ? 'opacity-100' : 'opacity-0'
            }`}
          />
        ))}
      </div>

      {displayable.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {displayable.map((src, index) => (
            <button
              key={src}
              type="button"
              onClick={() => pin(index)}
              aria-label={`Show photo ${index + 1}`}
              aria-pressed={index === activeIndex}
              className={`h-16 w-16 overflow-hidden rounded-lg border transition-colors ${
                index === activeIndex ? 'border-accent' : 'border-border-strong hover:border-accent/50'
              }`}
            >
              <img src={src} alt="" className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
