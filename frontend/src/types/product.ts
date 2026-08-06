/**
 * A single vehicle fitment entry for a product.
 *
 * Engine is deliberately absent: the catalog records fitment as make/model/year
 * only (`compatible_vehicles` in catalog.csv, e.g. "Ford Focus (2012-2018)"),
 * so there is no engine to show and guessing one would be inventing fitment.
 */
export interface VehicleCompatibility {
  make: string
  model: string
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
