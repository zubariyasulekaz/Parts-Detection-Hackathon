import { useState } from 'react'
import { PartIllustration } from '@/components/common/PartIllustration'
import { isDisplayableImageUrl } from '@/utils/format'

interface ProductThumbnailProps {
  category: string
  /** Candidate image URLs, in preference order. Non-http entries are ignored. */
  images?: string[]
  /**
   * `contain` shows the whole photo, so photos of differing aspect ratios fill
   * differing amounts of the tile. `cover` fills the tile edge to edge, which is
   * what a grid of side-by-side tiles needs to read as one row.
   */
  fit?: 'contain' | 'cover'
  className?: string
}

/**
 * A product's photo where one exists, falling back to the category glyph.
 *
 * Catalog photos are hosted absolute URLs (see `isDisplayableImageUrl`), so a
 * product with none — or one whose photo 404s — still renders a tile the same
 * size rather than a broken image.
 */
export function ProductThumbnail({ category, images = [], fit = 'contain', className = '' }: ProductThumbnailProps) {
  const displayable = images.filter(isDisplayableImageUrl)
  const [failed, setFailed] = useState(false)
  const src = displayable[0]

  if (!src || failed) {
    return <PartIllustration category={category} className={className} />
  }

  return (
    <div className={`relative overflow-hidden bg-linear-to-br from-surface-2 to-surface-3 ${className}`}>
      {/* Absolutely positioned so the photo never contributes to layout height.
          In flow, a portrait photo's natural height becomes the automatic
          minimum height of a flex item and overrides an `aspect-*` class on the
          wrapper — which made one tall product stretch its card taller than the
          rest of the row. Out of flow, the wrapper's own sizing always wins. */}
      <img
        src={src}
        alt={`${category} product photo`}
        loading="lazy"
        onError={() => setFailed(true)}
        className={`absolute inset-0 h-full w-full ${fit === 'cover' ? 'object-cover' : 'object-contain'}`}
      />
    </div>
  )
}
