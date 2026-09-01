import { apiGet, apiPostForm } from './client'
import type {
  PredictionResultDTO,
  ProductListQuery,
  ProductResponseDTO,
  RecommendationDTO,
} from '@/types/api'

/** Raw calls against the FastAPI backend. Returns wire-format DTOs - see src/adapters for domain mapping. */

/** Inference runs several models; give it far longer than a catalog read, but not forever. */
const PREDICT_TIMEOUT_MS = 120_000

/**
 * Where the catalogue routes live. Both constants move together: a search that
 * finds a SKU and then looks it up under a different prefix 404s on every
 * result.
 */
const CATALOG_PREFIX = import.meta.env.VITE_CATALOG_PREFIX ?? '/rigidhitch'
const PREDICT_PATH = import.meta.env.VITE_PREDICT_PATH ?? `${CATALOG_PREFIX}/predict`

export async function predictPart(file: File, topK: number, explain = true): Promise<PredictionResultDTO> {
  const formData = new FormData()
  formData.append('file', file)
  return apiPostForm<PredictionResultDTO>(PREDICT_PATH, formData, { top_k: topK, explain }, PREDICT_TIMEOUT_MS)
}




export async function fetchProduct(sku: string): Promise<ProductResponseDTO> {
  return apiGet<ProductResponseDTO>(`${CATALOG_PREFIX}/products/${encodeURIComponent(sku)}`)
}

export async function fetchProducts(query: ProductListQuery = {}): Promise<ProductResponseDTO[]> {
  return apiGet<ProductResponseDTO[]>(`${CATALOG_PREFIX}/products`, {
    limit: query.limit,
    offset: query.offset,
    category: query.category,
    brand: query.brand,
  })
}

export async function fetchRecommendations(sku: string): Promise<RecommendationDTO> {
  return apiGet<RecommendationDTO>(`${CATALOG_PREFIX}/products/${encodeURIComponent(sku)}/recommendations`)
}
