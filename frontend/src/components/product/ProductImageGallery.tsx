import { useState } from 'react'
import { PartIllustration } from '@/components/common/PartIllustration'
import { isDisplayableImageUrl } from '@/utils/format'

interface ProductImageGalleryProps {
  category: string
  images: string[]
}

export function ProductImageGallery({ category, images }: ProductImageGalleryProps) {
  const displayable = images.filter(isDisplayableImageUrl)
  const [activeIndex, setActiveIndex] = useState(0)

  if (displayable.length === 0) {
    return <PartIllustration category={category} className="aspect-square w-full rounded-xl" />
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="aspect-square overflow-hidden rounded-xl border border-border-strong bg-surface-2">
        <img
          src={displayable[activeIndex]}
          alt={`${category} photo ${activeIndex + 1} of ${displayable.length}`}
          className="h-full w-full object-contain"
        />
      </div>
      {displayable.length > 1 && (
        <div className="flex gap-2">
          {displayable.map((src, index) => (
            <button
              key={src}
              type="button"
              onClick={() => setActiveIndex(index)}
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
