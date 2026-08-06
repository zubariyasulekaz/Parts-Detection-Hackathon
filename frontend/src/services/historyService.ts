import { deleteHistoryEntry, fetchHistory } from '@/api/partpilotApi'
import { adaptPredictionHistoryEntry } from '@/adapters/historyAdapter'
import { MOCK_PREDICTION_HISTORY } from '@/mocks/history'
import { listProducts } from '@/services/catalogService'
import type { PredictionHistoryEntry, PredictionHistoryParams } from '@/types/history'

const API_MODE = import.meta.env.VITE_API_MODE

/** One page of the audit trail. Rows accumulate on every prediction, so an unbounded fetch is never wanted. */
const DEFAULT_HISTORY_LIMIT = 50

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function listPredictionHistory(params: PredictionHistoryParams = {}): Promise<PredictionHistoryEntry[]> {
  if (API_MODE === 'live') {
    const dtos = await fetchHistory({ limit: params.limit ?? DEFAULT_HISTORY_LIMIT, offset: params.offset })
    return dtos.map(adaptPredictionHistoryEntry)
  }

  await delay(180)
  const offset = params.offset ?? 0
  return MOCK_PREDICTION_HISTORY.slice(offset, offset + (params.limit ?? DEFAULT_HISTORY_LIMIT))
}

/**
 * Catalog photo for each SKU a run matched, keyed by SKU.
 *
 * An audit row records the SKU it matched but not that product's photo — it is a
 * snapshot of the run, and the catalog's photography can change after the fact.
 * The whole catalog is small enough to resolve in one request, so this fetches it
 * once for the page rather than one lookup per row.
 *
 * Never rejects: the matched-SKU photo is decoration on an already-loaded table,
 * so a catalog outage should leave the history readable rather than fail it.
 */
export async function getMatchedSkuImages(): Promise<Map<string, string>> {
  try {
    const products = await listProducts({ limit: 200 })
    return new Map(products.filter((p) => p.images.length > 0).map((p) => [p.sku, p.images[0]]))
  } catch {
    return new Map()
  }
}

/** Removes one recorded run. Resolves only once the backend confirms the deletion. */
export async function removePredictionHistoryEntry(id: number): Promise<void> {
  if (API_MODE === 'live') {
    await deleteHistoryEntry(id)
    return
  }
  await delay(180)
}
