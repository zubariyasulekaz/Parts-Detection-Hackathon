import { apiDelete, apiGet, apiPostForm } from './client'
import type {
  AuditEntryResponseDTO,
  HistoryListQuery,
  PredictionResultDTO,
  ProductListQuery,
  ProductResponseDTO,
  RecommendationDTO,
} from '@/types/api'

/** Raw calls against the FastAPI backend. Returns wire-format DTOs — see src/adapters for domain mapping. */

export async function predictPart(file: File, topK: number, explain = true): Promise<PredictionResultDTO> {
  const formData = new FormData()
  formData.append('file', file)
  return apiPostForm<PredictionResultDTO>('/predict', formData, { top_k: topK, explain })
}

export async function fetchHistory(query: HistoryListQuery = {}): Promise<AuditEntryResponseDTO[]> {
  return apiGet<AuditEntryResponseDTO[]>('/history', {
    limit: query.limit,
    offset: query.offset,
  })
}

/** Removes one recorded run. `entryId` is the audit row id from `fetchHistory`, not a SKU. */
export async function deleteHistoryEntry(entryId: number): Promise<{ id: number }> {
  return apiDelete<{ id: number }>(`/history/${entryId}`)
}

export async function fetchProduct(sku: string): Promise<ProductResponseDTO> {
  return apiGet<ProductResponseDTO>(`/products/${encodeURIComponent(sku)}`)
}

export async function fetchProducts(query: ProductListQuery = {}): Promise<ProductResponseDTO[]> {
  return apiGet<ProductResponseDTO[]>('/products', {
    limit: query.limit,
    offset: query.offset,
    category: query.category,
    brand: query.brand,
  })
}

export async function fetchRecommendations(sku: string): Promise<RecommendationDTO> {
  return apiGet<RecommendationDTO>(`/products/${encodeURIComponent(sku)}/recommendations`)
}
