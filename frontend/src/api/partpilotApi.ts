import { apiDelete, apiGet, apiPostForm, apiPostJson } from './client'
import type {
  AuditEntryResponseDTO,
  ChatStateDTO,
  HistoryListQuery,
  PredictionResultDTO,
  ProductListQuery,
  ProductResponseDTO,
  RecommendationDTO,
} from '@/types/api'

/** Raw calls against the FastAPI backend. Returns wire-format DTOs - see src/adapters for domain mapping. */

/** Inference runs several models; give it far longer than a catalog read, but not forever. */
const PREDICT_TIMEOUT_MS = 120_000

export async function predictPart(file: File, topK: number, explain = true): Promise<PredictionResultDTO> {
  const formData = new FormData()
  formData.append('file', file)
  return apiPostForm<PredictionResultDTO>('/predict', formData, { top_k: topK, explain }, PREDICT_TIMEOUT_MS)
}

/**
 * Records which SKU the user settled on for a recorded run - the audit
 * trail's feedback loop. `auditId` comes from the `/predict` response.
 */
export async function confirmPrediction(
  auditId: number,
  confirmedSku: string,
  disambiguation?: Record<string, string>,
): Promise<AuditEntryResponseDTO> {
  return apiPostJson<AuditEntryResponseDTO>(`/predict/${auditId}/confirm`, {
    confirmed_sku: confirmedSku,
    disambiguation: disambiguation ?? null,
  })
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

/**
 * Opens a guided-chat session over a prediction's candidates. The server
 * fetches every fact it asks about from the catalog - only SKUs and
 * similarity scores travel up.
 */
export async function startChat(
  candidates: { sku: string; similarity: number }[],
): Promise<ChatStateDTO> {
  return apiPostJson<ChatStateDTO>('/chat/start', { candidates })
}

/** Applies one turn: pick an option of the open question, or skip it ("Not sure"). */
export async function answerChat(
  sessionId: string,
  action: { optionIndex: number } | { skip: true },
): Promise<ChatStateDTO> {
  const body = 'skip' in action ? { skip: true } : { option_index: action.optionIndex }
  return apiPostJson<ChatStateDTO>(`/chat/${sessionId}/answer`, body)
}

/** Rewinds the answer trail to its first `keep` entries; `keep: 0` restarts. */
export async function undoChat(sessionId: string, keep: number): Promise<ChatStateDTO> {
  return apiPostJson<ChatStateDTO>(`/chat/${sessionId}/undo`, { keep })
}
