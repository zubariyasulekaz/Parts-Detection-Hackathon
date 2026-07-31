/**
 * Wire-format DTOs mirroring `partpilot/backend/schemas/*.py` exactly
 * (field names included). Nothing outside `src/api` and `src/services`
 * should import these directly — everything else consumes the adapted
 * domain types in `src/types/product.ts` and `src/types/identification.ts`.
 */

export interface ApiEnvelope<T> {
  success: boolean
  message: string
  data: T | null
}

export interface ApiErrorBody {
  success: false
  error_code: string
  message: string
}

export interface SearchResultDTO {
  sku: string
  similarity_score: number
}

/** Mirrors `backend.schemas.prediction.PredictionResponse` (Brain 1 + Brain 2 output only). */
export interface PredictionResponseDTO {
  predicted_category: string
  confidence: number
  search_time_ms: number
  results: SearchResultDTO[]
}

/** Mirrors `backend.schemas.catalog.VehicleCompatibility`. */
export interface VehicleCompatibilityDTO {
  make: string
  model: string
  year: number
}

/** Mirrors `backend.schemas.catalog.ProductResponse`. */
export interface ProductResponseDTO {
  sku: string
  product_name: string
  brand: string
  category: string
  description: string | null
  image_paths: string[]
  replacement_sku: string | null
  alternative_skus: string[]
  accessory_skus: string[]
  compatible_vehicles: VehicleCompatibilityDTO[]
  created_at: string
  updated_at: string
}

/** Mirrors `backend.schemas.recommendation.Recommendation`. */
export interface RecommendationDTO {
  alternatives: ProductResponseDTO[]
  accessories: ProductResponseDTO[]
}

/**
 * Mirrors `backend.schemas.prediction.PredictionResult` — the actual shape
 * `POST /predict` returns. `product`/`recommendation` are already resolved
 * server-side for the top-ranked SKU only; `explanation` is Brain 4's
 * (Qwen LLM) free-form natural-language output — present only when the
 * `explain` query param was true and the model loaded successfully.
 */
export interface PredictionResultDTO {
  prediction: PredictionResponseDTO
  product: ProductResponseDTO | null
  recommendation: RecommendationDTO | null
  explanation: string | null
}

export interface ProductListQuery {
  limit?: number
  offset?: number
  category?: string
  brand?: string
}
