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
  /** Server-side verdict: no result cleared the no-match threshold; `results` are context, not an answer. */
  no_match: boolean
  /** The similarity threshold the verdict was made against (per embedding backend). */
  no_match_threshold: number | null
  /** Embedding model that actually produced the scores (recorded on the index searched). */
  embedding_backend: string | null
  /** More than one entry means the classifier was uncertain and the runner-up category was searched too. */
  searched_categories: string[]
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
  manufacturer_part_number: string | null
  /** Free-form per-category visual facts; keys differ by category. */
  attributes: Record<string, string>
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
  /** Audit-trail row id for this run; POST the user's confirmed SKU to `/predict/{audit_id}/confirm`. */
  audit_id: number | null
}

/** Mirrors `backend.schemas.audit.AuditCandidate` — a `SearchResult` plus the rank it held, stored rather than derived. */
export interface AuditCandidateDTO {
  sku: string
  similarity_score: number
  rank: number
}

/**
 * Mirrors `backend.schemas.audit.AuditEntryResponse` — one recorded
 * `POST /predict` run. `thumbnail` is a self-contained base64 data URL of the
 * downscaled upload (there is no object storage yet), null when the row was
 * written without one.
 */
export interface AuditEntryResponseDTO {
  id: number
  created_at: string
  predicted_category: string
  confidence: number
  search_time_ms: number
  top_sku: string | null
  candidates: AuditCandidateDTO[]
  embedding_backend: string | null
  explanation: string | null
  thumbnail: string | null
  /** SKU the user settled on, when they told us. Differing from `top_sku` marks a correction. */
  confirmed_sku: string | null
  confirmed_at: string | null
  /** Guided-question answers (facet -> chosen value) that led to the confirmation. */
  disambiguation: Record<string, string> | null
}

export interface ProductListQuery {
  limit?: number
  offset?: number
  category?: string
  brand?: string
}

export interface HistoryListQuery {
  limit?: number
  offset?: number
}
