import type { AuditCandidateDTO, AuditEntryResponseDTO } from '@/types/api'
import type { PredictionHistoryCandidate, PredictionHistoryEntry } from '@/types/history'
import { formatCategoryLabel } from '@/utils/format'

function adaptPredictionHistoryCandidate(dto: AuditCandidateDTO): PredictionHistoryCandidate {
  // Unlike `/predict`, an audit row carries its own `rank` — the JSONB column's
  // element order is not dependable, so rank is never re-derived from position.
  return {
    sku: dto.sku,
    similarity: dto.similarity_score,
    rank: dto.rank,
  }
}

export function adaptPredictionHistoryEntry(dto: AuditEntryResponseDTO): PredictionHistoryEntry {
  return {
    id: dto.id,
    createdAt: dto.created_at,
    // Rows keep Brain 1's raw label ("oil_filter"); this is the same display
    // form adaptPredictionResponse produces for a live prediction.
    category: formatCategoryLabel(dto.predicted_category),
    confidence: dto.confidence,
    searchTimeMs: dto.search_time_ms,
    topSku: dto.top_sku,
    candidates: dto.candidates.map(adaptPredictionHistoryCandidate),
    embeddingBackend: dto.embedding_backend,
    explanation: dto.explanation,
    thumbnail: dto.thumbnail,
  }
}
