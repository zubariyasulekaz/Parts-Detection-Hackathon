/** One ranked SKU exactly as the similarity search returned it - a snapshot of that run, not a live catalog lookup. */
export interface PredictionHistoryCandidate {
  sku: string
  similarity: number
  rank: number
}

/** A recorded `POST /predict` run, normalized from the backend's audit-trail row. */
export interface PredictionHistoryEntry {
  /** Audit table primary key - safe as a list key, and the only stable handle on a run. Not a SKU. */
  id: number
  /** ISO-8601 timestamp from the backend, left as a string and formatted at render time. */
  createdAt: string
  category: string
  confidence: number
  searchTimeMs: number
  /** Null when the run produced no ranked match to record. */
  topSku: string | null
  candidates: PredictionHistoryCandidate[]
  /** Which Brain 2 embedding backend ran (`dinov2`, `openclip`, …) - knowing this is half the point of the audit trail. */
  embeddingBackend: string | null
  /** Brain 4's explanation as it was recorded; null when the run skipped it or the model never loaded. */
  explanation: string | null
  /**
   * The uploaded image, downscaled to a base64 `data:` URL at prediction time. `isDisplayableImageUrl`
   * rejects `data:` URLs, so test truthiness instead and fall back to `PartIllustration`.
   */
  thumbnail: string | null
  /** SKU the user settled on, when they told us. Differing from `topSku` marks a correction. */
  confirmedSku?: string | null
}

export interface PredictionHistoryParams {
  limit?: number
  offset?: number
}
