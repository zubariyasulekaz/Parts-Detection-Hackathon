import { History } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { HistoryEntryCard } from '@/components/history/HistoryEntryCard'
import { HistoryTable } from '@/components/history/HistoryTable'
import { PageContainer } from '@/components/layout/PageContainer'
import { listPredictionHistory } from '@/services/historyService'
import type { PredictionHistoryEntry } from '@/types/history'

type LoadStatus = 'loading' | 'success' | 'error'

export function HistoryPage() {
  const navigate = useNavigate()
  const [entries, setEntries] = useState<PredictionHistoryEntry[]>([])
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  // The fetch has no natural dependency, so bumping this is what makes Retry actually refetch.
  const [reloadToken, setReloadToken] = useState(0)

  useEffect(() => {
    let cancelled = false
    setStatus('loading')
    listPredictionHistory()
      .then((result) => {
        if (cancelled) return
        setEntries(result)
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

          <HistoryTable entries={entries} expandedId={expandedId} onToggleExplanation={toggleExplanation} />

          <div className="flex flex-col gap-3 sm:hidden">
            {entries.map((entry) => (
              <HistoryEntryCard
                key={entry.id}
                entry={entry}
                isExpanded={expandedId === entry.id}
                onToggleExplanation={() => toggleExplanation(entry.id)}
              />
            ))}
          </div>
        </>
      )}
    </PageContainer>
  )
}
