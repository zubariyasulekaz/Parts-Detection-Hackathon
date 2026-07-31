import { HERO_PART_SVG_MARKUP } from '@/assets/illustrations'

const SAMPLE_FILE_NAME = 'sample-shock-absorber.png'
const SAMPLE_DIMENSION_PX = 800

let cachedSampleImage: Promise<File> | null = null

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('Could not render the sample image.'))
    img.src = src
  })
}

async function renderSampleImage(): Promise<File> {
  const svgBlob = new Blob([HERO_PART_SVG_MARKUP], { type: 'image/svg+xml' })
  const svgUrl = URL.createObjectURL(svgBlob)

  try {
    const image = await loadImage(svgUrl)
    const canvas = document.createElement('canvas')
    canvas.width = SAMPLE_DIMENSION_PX
    canvas.height = SAMPLE_DIMENSION_PX
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('Canvas rendering is not supported in this browser.')
    ctx.drawImage(image, 0, 0, SAMPLE_DIMENSION_PX, SAMPLE_DIMENSION_PX)

    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'))
    if (!blob) throw new Error('Could not generate the sample image.')
    return new File([blob], SAMPLE_FILE_NAME, { type: 'image/png' })
  } finally {
    URL.revokeObjectURL(svgUrl)
  }
}

/** Real, backend-decodable PNG bytes for the "Try Sample Image" action — cached after first render. */
export function getSampleImageFile(): Promise<File> {
  if (!cachedSampleImage) {
    cachedSampleImage = renderSampleImage().catch((error: unknown) => {
      cachedSampleImage = null
      throw error
    })
  }
  return cachedSampleImage
}
