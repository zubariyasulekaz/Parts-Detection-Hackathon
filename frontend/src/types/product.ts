/** A single vehicle fitment entry for a product. */
export interface VehicleCompatibility {
  make: string
  model: string
  /** Not modeled by the current backend catalog schema; only ever populated in mock data. */
  engine?: string
  yearStart: number
  yearEnd: number
}

/** A catalog product, normalized from the backend's `ProductResponse` shape. */
export interface Product {
  sku: string
  productName: string
  brand: string
  category: string
  description: string
  /** Resolved, ready-to-render image URLs. Empty when no photography exists yet. */
  images: string[]
  replacementSku: string | null
  alternativeSkus: string[]
  accessorySkus: string[]
  compatibleVehicles: VehicleCompatibility[]
}

/** Resolved alternative/accessory/replacement products for a given SKU. */
export interface ProductRelationships {
  replacement: Product | null
  alternatives: Product[]
  accessories: Product[]
}

export interface ProductListParams {
  category?: string
  brand?: string
  query?: string
  limit?: number
}
