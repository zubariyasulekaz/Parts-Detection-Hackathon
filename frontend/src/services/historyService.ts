import { fetchHistory } from '@/api/partpilotApi'
import { adaptPredictionHistoryEntry } from '@/adapters/historyAdapter'
import { MOCK_PREDICTION_HISTORY } from '@/mocks/history'
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
