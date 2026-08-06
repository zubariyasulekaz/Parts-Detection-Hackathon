import { predictPart } from '@/api/partpilotApi'
import { adaptPredictionResult } from '@/adapters/identificationAdapter'
import {
  getScenarioById,
  pickScenarioForFile,
  resolveScenarioCandidates,
  SAMPLE_IMAGE_SCENARIO_ID,
} from '@/mocks/identificationResults'
import { getProduct } from './catalogService'
import type { IdentificationCandidate, IdentificationResult, ProcessingStageKey } from '@/types/identification'

const API_MODE = import.meta.env.VITE_API_MODE
const TOP_K = Number(import.meta.env.VITE_PREDICTION_TOP_K) || 5
/** Opt out of Brain 4 when its weights are unavailable — the LLM load otherwise stalls the request. */
const EXPLAIN = import.meta.env.VITE_PREDICTION_EXPLAIN !== 'false'

/**
 * Confirmation + confidence rules live here, not in a component, so the
 * thresholds are easy to find and tune independently of the UI.
 */

/** Candidates within this similarity gap of the top match require explicit user confirmation. */
export const CONFIRMATION_SIMILARITY_GAP = 0.05

/** Category confidence at or above this is surfaced as a "high-confidence identification". */
export const HIGH_CONFIDENCE_THRESHOLD = 0.9

/** Similarity gap above this between rank 1 and rank 2 is called "strong separation" in the AI match summary. */
export const STRONG_SEPARATION_GAP = 0.08

export interface ProcessingStageDefinition {
  key: ProcessingStageKey
  activeLabel: string
  completedLabel: string
}

/** Stage order + copy for the processing UI — corresponds 1:1 to the real pipeline (see docs/architecture). */
export const PROCESSING_STAGE_DEFINITIONS: ProcessingStageDefinition[] = [
  { key: 'validate', activeLabel: 'Validating image quality', completedLabel: 'Image quality validated' },
  { key: 'normalize', activeLabel: 'Normalizing image', completedLabel: 'Image normalized' },
  { key: 'classify', activeLabel: 'Identifying part category', completedLabel: 'Part category identified' },
  { key: 'embed', activeLabel: 'Generating visual embedding', completedLabel: 'Visual embedding generated' },
  { key: 'search', activeLabel: 'Searching the visual catalog', completedLabel: 'Catalog searched' },
  {
    key: 'retrieve',
    activeLabel: 'Retrieving product intelligence',
    completedLabel: 'Product intelligence retrieved',
  },
]

const PROCESSING_STAGES: ProcessingStageKey[] = PROCESSING_STAGE_DEFINITIONS.map((definition) => definition.key)

const MOCK_STAGE_DELAYS_MS: Record<ProcessingStageKey, number> = {
  validate: 320,
  normalize: 420,
  classify: 680,
  embed: 620,
  search: 520,
  retrieve: 480,
}

export interface IdentifyOptions {
  /** Called once per pipeline stage as it completes, in order — drives the processing UI. */
  onStage?: (stage: ProcessingStageKey) => void
  /** True when the request came from "Try Sample Image" — always resolves to the golden-path scenario. */
  useSampleScenario?: boolean
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function computeConfirmation(candidates: IdentificationCandidate[]): {
  requiresConfirmation: boolean
  confirmationReason?: string
} {
  if (candidates.length < 2) return { requiresConfirmation: false }
  const gap = candidates[0].similarity - candidates[1].similarity
  if (gap >= CONFIRMATION_SIMILARITY_GAP) return { requiresConfirmation: false }
  return {
    requiresConfirmation: true,
    confirmationReason:
      'The top candidates have similar visual similarity scores. User confirmation helps reduce incorrect-part recommendations.',
  }
}

async function runMockPipeline(
  file: File,
  uploadedImageUrl: string,
  options: IdentifyOptions,
): Promise<IdentificationResult> {
  const scenario = options.useSampleScenario
    ? getScenarioById(SAMPLE_IMAGE_SCENARIO_ID)
    : pickScenarioForFile(file)

  for (const stage of PROCESSING_STAGES) {
    await delay(MOCK_STAGE_DELAYS_MS[stage])
    options.onStage?.(stage)
  }

  const candidates = resolveScenarioCandidates(scenario)
  const { requiresConfirmation, confirmationReason } = computeConfirmation(candidates)

  return {
    uploadedImageUrl,
    imageQuality: scenario.imageQuality,
    category: { name: scenario.categoryName, confidence: scenario.confidence },
    candidates,
    requiresConfirmation,
    confirmationReason,
    selectedSku: requiresConfirmation ? null : (candidates[0]?.sku ?? null),
    searchTimeMs: scenario.searchTimeMs,
    aiExplanation: scenario.explanation,
  }
}

async function runLivePipeline(
  file: File,
  uploadedImageUrl: string,
  options: IdentifyOptions,
): Promise<IdentificationResult> {
  options.onStage?.('validate')
  options.onStage?.('normalize')

  const prediction = adaptPredictionResult(await predictPart(file, TOP_K, EXPLAIN))
  options.onStage?.('classify')
  options.onStage?.('embed')
  options.onStage?.('search')

  // The backend already resolves catalog metadata for the top-ranked SKU
  // (Brain 3, joined server-side into `product`); only ranks 2/3 need a
  // separate per-SKU lookup here.
  const candidates = await Promise.all(
    prediction.rankedResults.slice(0, 3).map(async (result, index): Promise<IdentificationCandidate> => {
      if (index === 0 && prediction.topProduct) {
        const product = prediction.topProduct
        return {
          sku: result.sku,
          productName: product.productName,
          brand: product.brand,
          category: product.category,
          similarity: result.similarity,
          rank: result.rank,
          imageUrl: product.images[0],
        }
      }
      try {
        const product = await getProduct(result.sku)
        return {
          sku: result.sku,
          productName: product.productName,
          brand: product.brand,
          category: product.category,
          similarity: result.similarity,
          rank: result.rank,
          imageUrl: product.images[0],
        }
      } catch {
        return {
          sku: result.sku,
          productName: result.sku,
          brand: 'Unknown',
          category: prediction.categoryName,
          similarity: result.similarity,
          rank: result.rank,
        }
      }
    }),
  )
  options.onStage?.('retrieve')

  const { requiresConfirmation, confirmationReason } = computeConfirmation(candidates)

  return {
    uploadedImageUrl,
    // The backend validates the image before running the pipeline; reaching
    // this point means it passed that check. No separate quality score exists.
    imageQuality: 'good',
    category: { name: prediction.categoryName, confidence: prediction.confidence },
    candidates,
    requiresConfirmation,
    confirmationReason,
    selectedSku: requiresConfirmation ? null : (candidates[0]?.sku ?? null),
    searchTimeMs: prediction.searchTimeMs,
    aiExplanation: prediction.explanation,
  }
}

export async function identify(
  file: File,
  uploadedImageUrl: string,
  options: IdentifyOptions = {},
): Promise<IdentificationResult> {
  return API_MODE === 'live'
    ? runLivePipeline(file, uploadedImageUrl, options)
    : runMockPipeline(file, uploadedImageUrl, options)
}
