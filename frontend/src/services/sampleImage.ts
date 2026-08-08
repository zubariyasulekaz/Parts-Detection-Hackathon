export interface PartSample {
  /**
   * Brain 1 category slug. Doubles as the asset filename and as the key mock
   * mode matches a canned scenario on, so it must stay in sync with
   * `backend.core.constants.PLACEHOLDER_CATEGORY_LABELS`.
   */
  slug: string
  /** Catalog category name, as `resolve_catalog_category` would return it. */
  category: string
  sku: string
  productName: string
  /** Served from `public/samples/`, so the browser can fetch real image bytes for the sample upload. */
  src: string
}

function sampleSrc(slug: string): string {
  return `${import.meta.env.BASE_URL}samples/${slug}.jpg`
}

/**
 * One real catalog photo per category the classifier can predict - the landing
 * page cycles through these, and "Try Sample Image" submits whichever is
 * showing. Real photos rather than an illustration so a sample run exercises
 * the same path a user's own upload would, and actually matches the catalog.
 */
export const PART_SAMPLES: PartSample[] = [
  {
    slug: 'brake-pads',
    category: 'Brake Pads',
    sku: 'BP-1002',
    productName: 'Duralast Gold Heavy-Duty Front Brake Pad Set',
    src: sampleSrc('brake-pads'),
  },
  {
    slug: 'oil-filter',
    category: 'Oil Filter',
    sku: 'OF-1003',
    productName: 'Bosch Premium FILTECH Spin-On Oil Filter',
    src: sampleSrc('oil-filter'),
  },
  {
    slug: 'air-filter',
    category: 'Air Filter',
    sku: 'AFR-001',
    productName: 'OEM Rectangular Panel Air Filter',
    src: sampleSrc('air-filter'),
  },
  {
    slug: 'exhaust-manifold',
    category: 'Exhaust Manifold',
    sku: 'EXM-1001',
    productName: 'OEM Cast Iron Exhaust Manifold',
    src: sampleSrc('exhaust-manifold'),
  },
  {
    slug: 'shock-absorber',
    category: 'Shock Absorber',
    sku: 'SHK-1001',
    productName: 'OEM Front Strut Assembly Pair',
    src: sampleSrc('shock-absorber'),
  },
  {
    slug: 'wheel-hub-assembly',
    category: 'Wheel Hub Assembly',
    sku: 'WHA-1001',
    productName: 'Wheel Hub Assembly with ABS Sensor',
    src: sampleSrc('wheel-hub-assembly'),
  },
  {
    slug: 'throttle-body',
    category: 'Throttle Body',
    sku: 'TB-1001',
    productName: 'Electronic Throttle Body',
    src: sampleSrc('throttle-body'),
  },
  {
    slug: 'fuel-injector',
    category: 'Fuel Injector',
    sku: 'FI-1001',
    productName: 'Port Fuel Injector',
    src: sampleSrc('fuel-injector'),
  },
  {
    slug: 'power-steering-pump',
    category: 'Power Steering Pump',
    sku: 'PSP-1001',
    productName: 'Hydraulic Power Steering Pump',
    src: sampleSrc('power-steering-pump'),
  },
  {
    slug: 'suspension-bushing',
    category: 'Suspension Bushing',
    sku: 'SBH-1001',
    productName: 'Control Arm Bushing Pair',
    src: sampleSrc('suspension-bushing'),
  },
]

/** File name prefix; `identificationResults` reads the slug back out of it to pick a mock scenario. */
export const SAMPLE_FILE_PREFIX = 'sample-'

const cache = new Map<string, Promise<File>>()

async function fetchSampleFile(sample: PartSample): Promise<File> {
  const response = await fetch(sample.src)
  if (!response.ok) {
    throw new Error(`Could not load the ${sample.category} sample image.`)
  }
  const blob = await response.blob()
  return new File([blob], `${SAMPLE_FILE_PREFIX}${sample.slug}.jpg`, { type: 'image/jpeg' })
}

/** Real JPEG bytes for "Try Sample Image" - cached per sample after the first fetch. */
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
