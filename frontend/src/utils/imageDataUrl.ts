/**
 * Downscale a file to a JPEG data URL small enough to keep in
 * sessionStorage. Object URLs die with the document, so a refresh on the
 * results page needs its own self-contained copy of the upload.
 */
export async function fileToDataUrl(file: File, maxSide = 512, quality = 0.8): Promise<string | null> {
  try {
    const bitmap = await createImageBitmap(file)
    try {
      const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height))
      const canvas = document.createElement('canvas')
      canvas.width = Math.max(1, Math.round(bitmap.width * scale))
      canvas.height = Math.max(1, Math.round(bitmap.height * scale))
      const context = canvas.getContext('2d')
      if (!context) return null
      context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
      return canvas.toDataURL('image/jpeg', quality)
    } finally {
      bitmap.close()
    }
  } catch {
    return null
  }
}
