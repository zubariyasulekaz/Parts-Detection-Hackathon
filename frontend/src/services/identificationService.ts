import { predictPart } from '@/api/partpilotApi'
import { adaptPredictionResult } from '@/adapters/identificationAdapter'
import { getSampleScenario, pickScenarioForFile, resolveScenarioCandidates } from '@/mocks/identificationResults'
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

/**
 * Below this visual similarity, the top-ranked SKU is not a plausible match.
 *
 * Brain 2 always returns the nearest neighbours inside the predicted category —
 * it has no way to answer "nothing in here looks like this". So a photo of a part
 * we don't stock still comes back with a ranked list, just at a much lower cosine
 * similarity. Treating that as a catalog match is worse than saying nothing:
 * it recommends the wrong part with a confident-looking UI.
 *
 * Calibrated against all 225 catalog images rather than guessed. Scores here are
 * DINOv2/OpenCLIP cosine against a product centroid (the mean of that product's
 * photos), which sits far lower than intuition suggests — a correct match has a
 * median of 0.90 but a floor of 0.55, and even an exact catalog photo scores ~0.70
 * because it is compared against the average of its product's other photos, not
 * against itself. Measured trade-off:
 *
 *     threshold   correct matches rejected   out-of-catalog caught
 *       0.45              0.0%                      84.5%
 *       0.50              0.0%                      85.8%   <- chosen
 *       0.55              0.4%                      86.5%
 *       0.65              2.7%                      87.3%
 *
 * 0.50 is the highest value that rejects no correct match in the catalog; going
 * higher buys almost no extra detection and starts calling stocked parts missing,
 * which costs a sale where a low-confidence match merely costs a second look.
 */
export const NO_CATALOG_MATCH_THRESHOLD = 0.5

/** True when even the closest catalog entry is too far off to present as a match. */
export function hasNoCatalogMatch(candidates: IdentificationCandidate[]): boolean {
  const top = candidates[0]
  return !top || top.similarity < NO_CATALOG_MATCH_THRESHOLD
}

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

/**
 * Resolves the two flags the results UI branches on. Kept together because the
 * "no catalog match" verdict outranks the ambiguity one: when nothing matched
 * closely enough, asking the user to pick between three bad candidates — or
 * quietly pre-selecting the least bad — would both be misleading.
 */
function computeOutcome(candidates: IdentificationCandidate[]): {
  requiresConfirmation: boolean
  confirmationReason?: string
  selectedSku: string | null
} {
  if (hasNoCatalogMatch(candidates)) {
    return { requiresConfirmation: false, selectedSku: null }
  }
  const topSku = candidates[0].sku
  if (candidates.length < 2) return { requiresConfirmation: false, selectedSku: topSku }

  const gap = candidates[0].similarity - candidates[1].similarity
  if (gap >= CONFIRMATION_SIMILARITY_GAP) return { requiresConfirmation: false, selectedSku: topSku }
  return {
    requiresConfirmation: true,
    confirmationReason:
      'The top candidates have similar visual similarity scores. User confirmation helps reduce incorrect-part recommendations.',
    selectedSku: null,
  }
}

async function runMockPipeline(
  file: File,
  uploadedImageUrl: string,
  options: IdentifyOptions,
): Promise<IdentificationResult> {
  const scenario = options.useSampleScenario ? getSampleScenario(file) : pickScenarioForFile(file)

  for (const stage of PROCESSING_STAGES) {
    await delay(MOCK_STAGE_DELAYS_MS[stage])
    options.onStage?.(stage)
  }

  const candidates = resolveScenarioCandidates(scenario)
  const { requiresConfirmation, confirmationReason, selectedSku } = computeOutcome(candidates)

  return {
    uploadedImageUrl,
    imageQuality: scenario.imageQuality,
    category: { name: scenario.categoryName, confidence: scenario.confidence },
    candidates,
    requiresConfirmation,
    confirmationReason,
    selectedSku,
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
          compatibleVehicles: product.compatibleVehicles,
          manufacturerPartNumber: product.manufacturerPartNumber,
          attributes: product.attributes,
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
          compatibleVehicles: product.compatibleVehicles,
          manufacturerPartNumber: product.manufacturerPartNumber,
          attributes: product.attributes,
        }
      } catch {
        // No catalog metadata for this SKU, so no fitment to ask about. The
        // guided questions treat an empty list as "unknown", not "fits nothing".
        return {
          sku: result.sku,
          productName: result.sku,
          brand: 'Unknown',
          category: prediction.categoryName,
          similarity: result.similarity,
          rank: result.rank,
          compatibleVehicles: [],
          manufacturerPartNumber: null,
          attributes: {},
        }
      }
    }),
  )
  options.onStage?.('retrieve')

  const { requiresConfirmation, confirmationReason, selectedSku } = computeOutcome(candidates)

  return {
    uploadedImageUrl,
    // The backend validates the image before running the pipeline; reaching
    // this point means it passed that check. No separate quality score exists.
    imageQuality: 'good',
    category: { name: prediction.categoryName, confidence: prediction.confidence },
    candidates,
    requiresConfirmation,
    confirmationReason,
    selectedSku,
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
