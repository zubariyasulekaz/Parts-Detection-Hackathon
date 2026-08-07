import type { VehicleCompatibility } from './product'

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
  /**
   * Fitment from Brain 3, carried onto the candidate so the results page can ask
   * which vehicle the part is for. Empty when the catalog lookup failed or the
   * SKU has no recorded fitment - see `services/disambiguation.ts`, which will
   * not ask a vehicle question it cannot answer for every candidate.
   */
  compatibleVehicles: VehicleCompatibility[]
  /** The number stamped on the part, when the catalog records one. */
  manufacturerPartNumber: string | null
  /** Visual facts from Brain 3 - what the user can answer by looking at the part. */
  attributes: Record<string, string>
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
   * Server-side verdict that nothing in the catalog scored high enough to
   * present as a match (mock mode derives it from the local threshold).
   */
  noMatch: boolean
  /** The similarity threshold that verdict was made against, when known. */
  noMatchThreshold: number | null
  /** Audit-trail row id - needed to post the user's confirmation back. Null in mock mode. */
  auditId: number | null
  /**
   * Brain 4's (Qwen LLM) free-form explanation, verbatim - displayed as-is,
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
