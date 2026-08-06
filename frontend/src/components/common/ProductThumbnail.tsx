import { useState } from 'react'
import { PartIllustration } from '@/components/common/PartIllustration'
import { isDisplayableImageUrl } from '@/utils/format'

interface ProductThumbnailProps {
  category: string
  /** Candidate image URLs, in preference order. Non-http entries are ignored. */
  images?: string[]
  className?: string
}

/**
 * A product's photo where one exists, falling back to the category glyph.
 *
 * Catalog photos are hosted absolute URLs (see `isDisplayableImageUrl`), so a
 * product with none — or one whose photo 404s — still renders a tile the same
 * size rather than a broken image.
 */
export function ProductThumbnail({ category, images = [], className = '' }: ProductThumbnailProps) {
  const displayable = images.filter(isDisplayableImageUrl)
  const [failed, setFailed] = useState(false)
  const src = displayable[0]

  if (!src || failed) {
    return <PartIllustration category={category} className={className} />
  }

  return (
    <div className={`overflow-hidden bg-linear-to-br from-surface-2 to-surface-3 ${className}`}>
      <img
        src={src}
        alt={`${category} product photo`}
        loading="lazy"
        onError={() => setFailed(true)}
        className="h-full w-full object-contain"
      />
    </div>
  )
}
