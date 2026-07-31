export interface CategoryPrediction {
  name: string
  confidence: number
}

export type ImageQuality = 'good' | 'fair' | 'poor'

/** One catalog SKU returned by the visual similarity search, ranked by similarity. */
export interface IdentificationCandidate {
  sku: string
  productName: string
  brand: string
  category: string
  similarity: number
  rank: number
  imageUrl?: string
}

/** The full outcome of an identification run, ready for the Results page. */
export interface IdentificationResult {
  uploadedImageUrl: string
  imageQuality: ImageQuality
  category: CategoryPrediction
  candidates: IdentificationCandidate[]
  /** True when the top candidates are too close in score to auto-select safely. */
  requiresConfirmation: boolean
  confirmationReason?: string
  selectedSku: string | null
  searchTimeMs: number
  /**
   * Brain 4's (Qwen LLM) free-form explanation, verbatim — displayed as-is,
   * never parsed into structured UI. Null in mock mode's non-demo scenarios
   * and whenever live mode ran without `explain` or the model didn't load.
   */
  aiExplanation: string | null
}

export type IdentificationStatus = 'idle' | 'processing' | 'success' | 'ambiguous' | 'error'

export type ProcessingStageKey = 'validate' | 'normalize' | 'classify' | 'embed' | 'search' | 'retrieve'

export type ProcessingStageStatus = 'complete' | 'active' | 'pending'

export interface ProcessingStage {
  key: ProcessingStageKey
  label: string
  status: ProcessingStageStatus
}

/** Progress callback used by identificationService to drive the processing UI. */
export type ProcessingStageListener = (stage: ProcessingStageKey) => void
