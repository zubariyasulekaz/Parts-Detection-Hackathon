export interface PartSample {
  /** Doubles as the asset filename stem and the cache key. */
  slug: string
  /** Catalog category, as the product record stores it. */
  category: string
  sku: string
  productName: string
  /** Served from `public/samples/`, so the browser can fetch real image bytes for the sample upload. */
  src: string
  /** Image MIME type - these are a mix of PNG and JPEG, as they were photographed. */
  type: string
}

function sampleSrc(file: string): string {
  return `${import.meta.env.BASE_URL}samples/${file}`
}

/**
 * The photographs behind "Try Sample Image", cycled on the landing page.
 *
 * **These are real hand-taken photographs, not catalogue images.** A catalogue
 * photo submitted as a sample scores near 1.0 against itself and would put a
 * fabricated number in front of whoever is watching - the exact failure this
 * project has spent weeks avoiding. Each of these was taken with a phone, on a
 * bench or a vehicle, and returns the same ~0.7 a customer's own photograph
 * would.
 *
 * Chosen for spread rather than for flattery: lights, wiring, a hub cap, a
 * spindle washer, a tie-down and a plough edge. Someone clicking through them
 * sees the range of the catalogue, not one lucky category.
 */
export const PART_SAMPLES: PartSample[] = [
  {
    slug: '021-256-10',
    category: 'Trailer Parts - Hubs & Drums',
    sku: '021-256-10',
    productName: 'ST-400D 4 Universal Valcrum Aluminum Threaded Hub Cap',
    src: sampleSrc('021-256-10.png'),
    type: 'image/png',
  },
  {
    slug: 'tll73fb',
    category: 'Lights',
    sku: 'TLL73FB',
    productName: 'Opti-Brite LED Wide Angle Flood Beam Work Light',
    src: sampleSrc('tll73fb.png'),
    type: 'image/png',
  },
  {
    slug: '02411',
    category: 'Electrical - Wiring Essentials',
    sku: '02411',
    productName: '14 Gauge, 100 FT Green Wire',
    src: sampleSrc('02411.png'),
    type: 'image/png',
  },
  {
    slug: '01090',
    category: 'Cargo Management',
    sku: '01090',
    productName: 'Tie-Down - E-Track Rope Ring Attachment Point',
    src: sampleSrc('01090.png'),
    type: 'image/png',
  },
  {
    slug: '005-023-00',
    category: 'Trailer Parts - Hubs & Drums',
    sku: '005-023-00',
    productName: 'D-Style Axle Spindle Washer',
    src: sampleSrc('005-023-00.png'),
    type: 'image/png',
  },
  {
    slug: '011-5550',
    category: 'Lights',
    sku: '011-5550',
    productName: 'White LED Bullet Light - Clearance/Side Marker',
    src: sampleSrc('011-5550.png'),
    type: 'image/png',
  },
  {
    slug: '01077',
    category: 'Towing Accessories - Hitch Installation',
    sku: '01077',
    productName: 'Hitch Installation Hardware Kit for 41116',
    src: sampleSrc('01077.png'),
    type: 'image/png',
  },
  {
    slug: '002-5200',
    category: 'Lights',
    sku: '002-5200',
    productName: 'LED Mini Stainless Steel Accent Light',
    src: sampleSrc('002-5200.png'),
    type: 'image/png',
  },
  {
    slug: '0020500',
    category: 'Snow Plow',
    sku: '0020500',
    productName: 'Replacement Rubber Edge For Pro-Wing Plow Attachment',
    src: sampleSrc('0020500.jpg'),
    type: 'image/jpeg',
  },
]

/** File name prefix; the slug is read back out of it to identify the sample. */
export const SAMPLE_FILE_PREFIX = 'sample-'

const cache = new Map<string, Promise<File>>()

async function fetchSampleFile(sample: PartSample): Promise<File> {
  const response = await fetch(sample.src)
  if (!response.ok) {
    throw new Error(`Could not load the ${sample.productName} sample image.`)
  }
  const blob = await response.blob()
  const extension = sample.type === 'image/png' ? 'png' : 'jpg'
  return new File([blob], `${SAMPLE_FILE_PREFIX}${sample.slug}.${extension}`, { type: sample.type })
}

/** Real image bytes for "Try Sample Image" - cached per sample after the first fetch. */
export function getSampleImageFile(sample: PartSample): Promise<File> {
  const cached = cache.get(sample.slug)
  if (cached) return cached

  const pending = fetchSampleFile(sample).catch((error: unknown) => {
    cache.delete(sample.slug)
    throw error
  })
  cache.set(sample.slug, pending)
  return pending
}
