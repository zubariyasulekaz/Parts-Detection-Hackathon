import type { PredictionHistoryEntry } from '@/types/history'

/**
 * Mock audit trail used when VITE_API_MODE=mock. Shaped identically to the
 * post-adapter `PredictionHistoryEntry` domain type so historyService can serve
 * it (and a live `/history` payload) through the exact same interface. SKUs and
 * categories come from src/mocks/products.ts so a row's top match still resolves.
 *
 * Newest first, matching the order the backend returns. Timestamps are fixed
 * strings rather than Date.now() so mock output stays deterministic.
 *
 * Every `thumbnail` here is null: a real base64 JPEG would add kilobytes per row
 * for no demo value, and a null thumbnail is a shape live mode produces too
 * (best-effort recording can write a row without one), so the UI's fallback is
 * exercised rather than bypassed.
 *
 * Only src/services and src/mocks should ever import this file.
 */
export const MOCK_PREDICTION_HISTORY: PredictionHistoryEntry[] = [
  {
    id: 148,
    createdAt: '2026-08-06T09:41:22Z',
    category: 'Shock Absorbers',
    confidence: 0.94,
    searchTimeMs: 188,
    topSku: 'SA-2210',
    confirmedSku: 'SA-2210',
    candidates: [
      { sku: 'SA-2210', similarity: 0.92, rank: 1 },
      { sku: 'SA-2211', similarity: 0.76, rank: 2 },
    ],
    // Shock absorbers are one of the categories pinned to OpenCLIP in settings.
    embeddingBackend: 'openclip',
    explanation:
      "The uploaded photo matches SA-2210 (KYB Excel-G Gas Shock Absorber, Rear) with 92% visual similarity and 94% category confidence, clearly ahead of the alternative. This match looks reliable and doesn't need further confirmation.",
    thumbnail: null,
  },
  {
    id: 147,
    createdAt: '2026-08-06T08:57:04Z',
    category: 'Brake Pads',
    confidence: 0.89,
    searchTimeMs: 214,
    topSku: null,
    candidates: [
      { sku: 'BP-1042', similarity: 0.91, rank: 1 },
      { sku: 'BP-1043', similarity: 0.885, rank: 2 },
      { sku: 'BP-1044', similarity: 0.83, rank: 3 },
    ],
    embeddingBackend: 'dinov2',
    explanation:
      'This looks like a front ceramic disc brake pad set, but the top three catalog candidates - Bosch BP-1042, ACDelco BP-1043, and Brembo BP-1044 - are visually similar and score within a few points of each other. Is there a brand stamp visible on the backing plate? Is this for a Toyota Camry/RAV4 or a Honda Accord?',
    thumbnail: null,
  },
  {
    id: 146,
    createdAt: '2026-08-05T17:12:48Z',
    category: 'Oil Filter',
    confidence: 0.93,
    searchTimeMs: 176,
    topSku: 'OF-3978',
    // The user picked rank 2 in the guided flow - a recorded correction.
    confirmedSku: 'OF-45011',
    candidates: [
      { sku: 'OF-3978', similarity: 0.9, rank: 1 },
      { sku: 'OF-45011', similarity: 0.74, rank: 2 },
      { sku: 'OF-45023', similarity: 0.7, rank: 3 },
    ],
    embeddingBackend: 'dinov2',
    // Ran with explain=false - the common shape when Brain 4's weights are unavailable.
    explanation: null,
    thumbnail: null,
  },
  {
    id: 145,
    createdAt: '2026-08-05T16:03:31Z',
    category: 'Spark Plug',
    confidence: 0.96,
    searchTimeMs: 179,
    topSku: 'SP-6610',
    candidates: [
      { sku: 'SP-6610', similarity: 0.95, rank: 1 },
      { sku: 'SP-6611', similarity: 0.79, rank: 2 },
    ],
    embeddingBackend: 'dinov2',
    explanation:
      'The uploaded photo matches SP-6610 (NGK Iridium Long-Life Spark Plug) with 95% visual similarity and 96% category confidence, well ahead of the next candidate. This is a clear, unambiguous match, so no further confirmation is needed.',
    thumbnail: null,
  },
  {
    id: 144,
    createdAt: '2026-08-04T11:26:09Z',
    category: 'Exhaust Manifold',
    confidence: 0.97,
    searchTimeMs: 184,
    topSku: 'EXM001',
    candidates: [
      { sku: 'EXM001', similarity: 0.94, rank: 1 },
      { sku: 'EXM003', similarity: 0.81, rank: 2 },
      { sku: 'EXM002', similarity: 0.77, rank: 3 },
    ],
    embeddingBackend: 'dinov2',
    explanation:
      'The uploaded photo matches EXM001 (Walker Exhaust Manifold Assembly, Driver Side) with 94% visual similarity and 97% category confidence - well ahead of the next candidate. This is a clear, unambiguous match, so no further confirmation is needed.',
    thumbnail: null,
  },
  {
    id: 143,
    createdAt: '2026-08-04T10:48:55Z',
    category: 'Air Filter',
    confidence: 0.61,
    searchTimeMs: 243,
    // A weak run: nothing scored high enough to record a top match, and the
    // row predates Brain 2 reporting which backend produced the embedding.
    topSku: null,
    candidates: [
      { sku: 'AF-2210', similarity: 0.58, rank: 1 },
      { sku: 'AF-2211', similarity: 0.55, rank: 2 },
    ],
    embeddingBackend: null,
    explanation: null,
    thumbnail: null,
  },
]
