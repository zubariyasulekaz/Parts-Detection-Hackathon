/** Fractions of the image's own width/height: 0-1 from its top-left corner. */
export interface CropRegion {
  left: number
  top: number
  right: number
  bottom: number
}

/** Below this share of the frame a drag is almost certainly a stray click. */
export const MIN_CROP_FRACTION = 0.01

export function regionArea(region: CropRegion): number {
  return Math.max(0, region.right - region.left) * Math.max(0, region.bottom - region.top)
}

/**
 * Cut a region out of an image file, returning a new file to search with.
 *
 * Done in the browser rather than by sending coordinates to the server: the
 * search endpoint already takes an image, so cropping here needs no API change
 * and no new failure mode. The cost is one canvas draw.
 *
 * The region is stored as fractions, not pixels, because the box is drawn on
 * whatever size the image happens to be displayed at - a phone in portrait, a
 * desktop at 900px - while the crop has to be taken from the full-resolution
 * original. Pixels from one would be meaningless against the other.
 *
 * Encoded as JPEG at high quality: the source is a photograph, PNG would be
 * several times larger for no visible gain, and the upload has a size limit.
 */
export async function cropImageFile(
  file: File,
  region: CropRegion,
  quality = 0.92,
): Promise<File> {
  const bitmap = await createImageBitmap(file)
  try {
    const left = Math.round(region.left * bitmap.width)
    const top = Math.round(region.top * bitmap.height)
    // At least one pixel each way, so a degenerate box cannot produce a canvas
    // of zero size, which throws rather than failing gracefully.
    const width = Math.max(1, Math.round((region.right - region.left) * bitmap.width))
    const height = Math.max(1, Math.round((region.bottom - region.top) * bitmap.height))

    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Could not prepare the image for cropping.')
    context.drawImage(bitmap, left, top, width, height, 0, 0, width, height)

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', quality),
    )
    if (!blob) throw new Error('Could not prepare the image for cropping.')

    // A distinct name so an audit trail can tell a refined search from the
    // original upload rather than seeing two identical filenames.
    const base = file.name.replace(/\.[^.]+$/, '') || 'photo'
    return new File([blob], `${base}-selection.jpg`, { type: 'image/jpeg' })
  } finally {
    bitmap.close()
  }
}
