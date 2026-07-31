import { findMockProduct } from './products'
import type { IdentificationCandidate, ImageQuality } from '@/types/identification'

interface ScenarioCandidateSeed {
  sku: string
  similarity: number
}

export interface IdentificationScenario {
  id: string
  categoryName: string
  confidence: number
  imageQuality: ImageQuality
  searchTimeMs: number
  candidates: ScenarioCandidateSeed[]
  /**
   * A realistic stand-in for Brain 4's (Qwen LLM) `explain()` output, in the
   * same voice/format the real system prompt enforces: a short explanation,
   * plus clarifying questions only when genuinely ambiguous. Lets mock mode
   * demo the feature without a loaded model.
   */
  explanation: string
}

/**
 * Canned end-to-end outcomes used when VITE_API_MODE=mock. Each mirrors a
 * shape the real /predict + /products pipeline can plausibly produce: a
 * clear category confidence, and a ranked candidate list with similarity
 * scores pulled from the mock catalog so downstream product lookups
 * (brand, name, category) stay consistent with src/mocks/products.ts.
 */
export const IDENTIFICATION_SCENARIOS: IdentificationScenario[] = [
  {
    id: 'exhaust-manifold-high-confidence',
    categoryName: 'Exhaust Manifold',
    confidence: 0.97,
    imageQuality: 'good',
    searchTimeMs: 184,
    candidates: [
      { sku: 'EXM001', similarity: 0.94 },
      { sku: 'EXM003', similarity: 0.81 },
      { sku: 'EXM002', similarity: 0.77 },
    ],
    explanation:
      "The uploaded photo matches EXM001 (Walker Exhaust Manifold Assembly, Driver Side) with 94% visual similarity and 97% category confidence — well ahead of the next candidate. This is a clear, unambiguous match, so no further confirmation is needed.",
  },
  {
    id: 'brake-pads-high-confidence',
    categoryName: 'Brake Pads',
    confidence: 0.97,
    imageQuality: 'good',
    searchTimeMs: 181,
    candidates: [
      { sku: 'BP-1042', similarity: 0.95 },
      { sku: 'BP-1043', similarity: 0.79 },
      { sku: 'BP-1044', similarity: 0.74 },
    ],
    explanation:
      "The uploaded photo matches BP-1042 (Bosch QuietCast Ceramic Disc Brake Pad Set) with 95% visual similarity and 97% category confidence — well ahead of the next candidate. This is a clear, unambiguous match, so no further confirmation is needed.",
  },
  {
    id: 'brake-pads-ambiguous',
    categoryName: 'Brake Pads',
    confidence: 0.89,
    imageQuality: 'good',
    searchTimeMs: 201,
    candidates: [
      { sku: 'BP-1042', similarity: 0.91 },
      { sku: 'BP-1043', similarity: 0.885 },
      { sku: 'BP-1044', similarity: 0.83 },
    ],
    explanation:
      "This looks like a front ceramic disc brake pad set, but the top three catalog candidates — Bosch BP-1042, ACDelco BP-1043, and Brembo BP-1044 — are visually similar and score within a few points of each other. A few details would help narrow it down: Is there a brand stamp visible on the backing plate? Is this for a Toyota Camry/RAV4 or a Honda Accord? Are wear-indicator clips already fitted to the pad?",
  },
  {
    id: 'oil-filter-high-confidence',
    categoryName: 'Oil Filter',
    confidence: 0.93,
    imageQuality: 'fair',
    searchTimeMs: 176,
    candidates: [
      { sku: 'OF-3978', similarity: 0.9 },
      { sku: 'OF-45011', similarity: 0.74 },
      { sku: 'OF-45023', similarity: 0.7 },
    ],
    explanation:
      "The image matches OF-3978 (Mahle spin-on oil filter) with 90% visual similarity and 93% category confidence, clearly ahead of the other oil-filter candidates. This match looks reliable and doesn't need further confirmation.",
  },
  {
    id: 'spark-plug-high-confidence',
    categoryName: 'Spark Plug',
    confidence: 0.96,
    imageQuality: 'good',
    searchTimeMs: 179,
    candidates: [
      { sku: 'SP-6610', similarity: 0.95 },
      { sku: 'SP-6611', similarity: 0.79 },
    ],
    explanation:
      "The uploaded photo matches SP-6610 (NGK Iridium Long-Life Spark Plug) with 95% visual similarity and 96% category confidence, well ahead of the next candidate. This is a clear, unambiguous match, so no further confirmation is needed.",
  },
  {
    id: 'spark-plug-close-call',
    categoryName: 'Spark Plug',
    confidence: 0.86,
    imageQuality: 'good',
    searchTimeMs: 192,
    candidates: [
      { sku: 'SP-6610', similarity: 0.88 },
      { sku: 'SP-6611', similarity: 0.855 },
    ],
    explanation:
      "This appears to be an iridium or platinum spark plug, but NGK SP-6610 and Denso SP-6611 are nearly tied in visual similarity — spark plugs from different brands can look almost identical in a photo. Can you read any text or part number stamped on the hex or ceramic insulator? Do you know which brand was originally installed in the vehicle?",
  },
  {
    id: 'shock-absorbers-high-confidence',
    categoryName: 'Shock Absorbers',
    confidence: 0.94,
    imageQuality: 'good',
    searchTimeMs: 188,
    candidates: [
      { sku: 'SA-2210', similarity: 0.92 },
      { sku: 'SA-2211', similarity: 0.76 },
    ],
    explanation:
      "The uploaded photo matches SA-2210 (KYB Excel-G Gas Shock Absorber, Rear) with 92% visual similarity and 94% category confidence, clearly ahead of the alternative. This match looks reliable and doesn't need further confirmation.",
  },
]

/** "Try Sample Image" always resolves to the golden-path, high-confidence scenario. */
export const SAMPLE_IMAGE_SCENARIO_ID = 'shock-absorbers-high-confidence'

export function resolveScenarioCandidates(scenario: IdentificationScenario): IdentificationCandidate[] {
  return scenario.candidates.map((seed, index) => {
    const product = findMockProduct(seed.sku)
    return {
      sku: seed.sku,
      productName: product?.productName ?? seed.sku,
      brand: product?.brand ?? 'Unknown',
      category: product?.category ?? scenario.categoryName,
      similarity: seed.similarity,
      rank: index + 1,
    }
  })
}

/**
 * Deterministically maps an uploaded file to a scenario so the same file
 * always reproduces the same demo outcome, without reaching for Math.random.
 */
export function pickScenarioForFile(file: File): IdentificationScenario {
  const key = `${file.name}:${file.size}`
  let hash = 0
  for (let i = 0; i < key.length; i += 1) {
    hash = (hash * 31 + key.charCodeAt(i)) | 0
  }
  const index = Math.abs(hash) % IDENTIFICATION_SCENARIOS.length
  return IDENTIFICATION_SCENARIOS[index]
}

export function getScenarioById(id: string): IdentificationScenario {
  const scenario = IDENTIFICATION_SCENARIOS.find((entry) => entry.id === id)
  if (!scenario) {
    throw new Error(`Unknown identification scenario: ${id}`)
  }
  return scenario
}
