import { adaptProduct } from './productAdapter'
import type { PredictionResponseDTO, PredictionResultDTO } from '@/types/api'
import type { Product } from '@/types/product'
import { formatCategoryLabel } from '@/utils/format'

export interface RankedResult {
  sku: string
  similarity: number
  rank: number
}

export interface AdaptedPrediction {
  categoryName: string
  confidence: number
  searchTimeMs: number
  rankedResults: RankedResult[]
}

export interface AdaptedPredictionResult extends AdaptedPrediction {
  /** Already resolved server-side, top-ranked SKU only — null if no confident match. */
  topProduct: Product | null
  topAlternatives: Product[]
  topAccessories: Product[]
  /** Brain 4's (Qwen) free-form explanation + clarifying questions, verbatim. Null unless requested and available. */
  explanation: string | null
}

/**
 * Structural mapping only — `PredictionResponse.results` carries just
 * `{sku, similarity_score}`, so enriching ranked results *other than the
 * top one* with brand/name/category (a per-SKU catalog lookup) happens in
 * identificationService, not here.
 */
export function adaptPredictionResponse(dto: PredictionResponseDTO): AdaptedPrediction {
  return {
    categoryName: formatCategoryLabel(dto.predicted_category),
    confidence: dto.confidence,
    searchTimeMs: dto.search_time_ms,
    rankedResults: dto.results.map((result, index) => ({
      sku: result.sku,
      similarity: result.similarity_score,
      rank: index + 1,
    })),
  }
}

/** Maps the full `/predict` response — prediction + Brain 3/4 output already joined server-side. */
export function adaptPredictionResult(dto: PredictionResultDTO): AdaptedPredictionResult {
  return {
    ...adaptPredictionResponse(dto.prediction),
    topProduct: dto.product ? adaptProduct(dto.product) : null,
    topAlternatives: dto.recommendation?.alternatives.map(adaptProduct) ?? [],
    topAccessories: dto.recommendation?.accessories.map(adaptProduct) ?? [],
    explanation: dto.explanation,
  }
}
