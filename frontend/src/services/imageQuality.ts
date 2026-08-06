import type { ImageQuality } from '@/types/identification'

/**
 * Measures upload quality client-side, so the "Image quality" chip reports
 * something real instead of a constant. Two cheap signals on a downscaled
 * grayscale copy:
 *
 *  - sharpness: variance of a 3x3 Laplacian. Blurry photos have soft edges
 *    everywhere, which crushes this variance by orders of magnitude.
 *  - exposure: mean luma. Near-black or blown-out photos give the models
 *    little to work with even when technically sharp.
 *
 * Thresholds are heuristic by nature; they only decide a three-way label,
 * never whether the pipeline runs.
 */

const ANALYSIS_SIZE = 256

const SHARPNESS_POOR = 40
const SHARPNESS_FAIR = 120
const LUMA_DARK = 40
const LUMA_BRIGHT = 215

export async function assessImageQuality(file: File): Promise<ImageQuality> {
  try {
    const bitmap = await createImageBitmap(file)
    try {
      const scale = ANALYSIS_SIZE / Math.max(bitmap.width, bitmap.height)
      const width = Math.max(1, Math.round(bitmap.width * Math.min(1, scale)))
      const height = Math.max(1, Math.round(bitmap.height * Math.min(1, scale)))

      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const context = canvas.getContext('2d', { willReadFrequently: true })
      if (!context) return 'good'
      context.drawImage(bitmap, 0, 0, width, height)
      const { data } = context.getImageData(0, 0, width, height)

      const luma = new Float32Array(width * height)
      let lumaSum = 0
      for (let i = 0; i < luma.length; i++) {
        const value = 0.299 * data[i * 4] + 0.587 * data[i * 4 + 1] + 0.114 * data[i * 4 + 2]
        luma[i] = value
        lumaSum += value
      }
      const meanLuma = lumaSum / luma.length

      // Variance of the 3x3 Laplacian (4-neighbour), skipping the border.
      let sum = 0
      let sumSquares = 0
      let count = 0
      for (let y = 1; y < height - 1; y++) {
        for (let x = 1; x < width - 1; x++) {
          const i = y * width + x
          const lap = 4 * luma[i] - luma[i - 1] - luma[i + 1] - luma[i - width] - luma[i + width]
          sum += lap
          sumSquares += lap * lap
          count++
        }
      }
      if (!count) return 'good'
      const mean = sum / count
      const variance = sumSquares / count - mean * mean

      const badExposure = meanLuma < LUMA_DARK || meanLuma > LUMA_BRIGHT
      if (variance < SHARPNESS_POOR) return 'poor'
      if (variance < SHARPNESS_FAIR || badExposure) return 'fair'
      return 'good'
    } finally {
      bitmap.close()
    }
  } catch {
    // Analysis is advisory; an unreadable-for-analysis file still uploads.
    return 'good'
  }
}
