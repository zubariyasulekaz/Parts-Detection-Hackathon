import { History } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { HistoryEntryCard } from '@/components/history/HistoryEntryCard'
import { HistoryTable } from '@/components/history/HistoryTable'
import { PageContainer } from '@/components/layout/PageContainer'
import { getMatchedSkuImages, listPredictionHistory, removePredictionHistoryEntry } from '@/services/historyService'
import type { PredictionHistoryEntry } from '@/types/history'

type LoadStatus = 'loading' | 'success' | 'error'

export function HistoryPage() {
  const navigate = useNavigate()
  const [entries, setEntries] = useState<PredictionHistoryEntry[]>([])
  const [skuImages, setSkuImages] = useState<Map<string, string>>(new Map())
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  // The fetch has no natural dependency, so bumping this is what makes Retry actually refetch.
  const [reloadToken, setReloadToken] = useState(0)

  useEffect(() => {
    let cancelled = false
    setStatus('loading')
    // The catalog lookup only decorates rows and never rejects, so the history
    // still renders if it comes back empty.
    Promise.all([listPredictionHistory(), getMatchedSkuImages()])
      .then(([result, images]) => {
        if (cancelled) return
        setEntries(result)
        setSkuImages(images)
        setStatus('success')
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Could not load prediction history.')
        setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [reloadToken])

  /**
   * Removes the row only once the backend confirms it, so a failed delete leaves
   * the table showing what is actually still recorded.
   */
  async function handleDelete(id: number) {
    setDeleteError(null)
    setDeletingId(id)
    try {
      await removePredictionHistoryEntry(id)
      setEntries((current) => current.filter((entry) => entry.id !== id))
      setExpandedId((current) => (current === id ? null : current))
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Could not delete that history entry.')
    } finally {
      setDeletingId(null)
    }
  }

  /**
   * Held here rather than in the row components: the table and the card stack render the same
   * entries at different breakpoints, so one source of truth keeps an open explanation open
   * when the viewport crosses `sm`.
   */
  function toggleExplanation(id: number) {
    setExpandedId((current) => (current === id ? null : id))
  }

  return (
    <PageContainer className="py-12">
      <div className="mb-8 max-w-2xl">
        <h1 className="text-2xl font-bold text-foreground">Prediction History</h1>
        <p className="mt-2 text-sm text-muted">
          Every identification run PartPilot has recorded, newest first — the photo it was given, what it predicted, and
          which model served it.
        </p>
      </div>

      {status === 'loading' && <LoadingState label="Loading prediction history…" />}

      {status === 'error' && (
        <ErrorState
          message={error ?? 'Could not load prediction history. Please try again.'}
          onRetry={() => setReloadToken((token) => token + 1)}
        />
      )}

      {status === 'success' && entries.length === 0 && (
        <EmptyState
          icon={History}
          title="No predictions recorded yet"
          description="Identify a part from the landing page and the run will be recorded here."
          action={
            <button
              type="button"
              onClick={() => navigate('/')}
              className="mt-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
            >
              Go to Upload
            </button>
          }
        />
      )}

      {status === 'success' && entries.length > 0 && (
        <>
          <p className="mb-4 text-xs text-muted">Showing the {entries.length} most recent runs.</p>

          {deleteError && (
            <p role="alert" className="mb-4 rounded-lg border border-danger/30 bg-danger-muted/40 px-3 py-2 text-sm text-danger">
              {deleteError}
            </p>
          )}

          <HistoryTable
            entries={entries}
            expandedId={expandedId}
            skuImages={skuImages}
            deletingId={deletingId}
            onToggleExplanation={toggleExplanation}
            onDelete={handleDelete}
          />

          <div className="flex flex-col gap-3 sm:hidden">
            {entries.map((entry) => (
              <HistoryEntryCard
                key={entry.id}
                entry={entry}
                isExpanded={expandedId === entry.id}
                matchedSkuImage={entry.topSku ? skuImages.get(entry.topSku) : undefined}
                isDeleting={deletingId === entry.id}
                onToggleExplanation={() => toggleExplanation(entry.id)}
                onDelete={() => handleDelete(entry.id)}
              />
            ))}
          </div>
        </>
      )}
    </PageContainer>
  )
}
