import type { BatchRowState } from '@/components/batch/BatchMatchRow'

/**
 * The last batch run, kept alive while the tab is open.
 *
 * Opening one row's full result navigates away from the page, which unmounts it
 * and takes its state with it - so coming back showed an empty picker and the
 * run had to be repeated from scratch. Seventy seconds of searching, thrown away
 * by clicking one result.
 *
 * A module-level store rather than `sessionStorage` because the run holds `File`
 * objects and object URLs, neither of which survives being serialised. That
 * bounds it to the tab's lifetime, which is the right lifetime: a batch run is
 * something you are looking at now, not something to restore next week.
 */
interface BatchSession {
  rows: BatchRowState[]
  files: Map<string, File>
  /** True once a row's full result has been opened, so the results page can offer a way back. */
  cameFromBatch: boolean
}

const session: BatchSession = { rows: [], files: new Map(), cameFromBatch: false }

export function saveBatchSession(rows: BatchRowState[], files: Map<string, File>): void {
  session.rows = rows
  session.files = files
}

export function loadBatchSession(): { rows: BatchRowState[]; files: Map<string, File> } {
  return { rows: session.rows, files: session.files }
}

export function markCameFromBatch(value: boolean): void {
  session.cameFromBatch = value
}

/**
 * Whether the results page was reached from the batch list.
 *
 * Cleared by any ordinary search, so "Back to batch results" cannot linger on a
 * page the batch run had nothing to do with.
 */
export function cameFromBatch(): boolean {
  return session.cameFromBatch && session.rows.length > 0
}

export function clearBatchSession(): void {
  session.rows = []
  session.files = new Map()
  session.cameFromBatch = false
}
