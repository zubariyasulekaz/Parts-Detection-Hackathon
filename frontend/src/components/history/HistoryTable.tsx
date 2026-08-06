import { Sparkles } from 'lucide-react'
import { Fragment } from 'react'
import { ConfidenceGauge } from '@/components/common/ConfidenceGauge'
import { PartIllustration } from '@/components/common/PartIllustration'
import { StatusBadge } from '@/components/common/StatusBadge'
import { HIGH_CONFIDENCE_THRESHOLD } from '@/services/identificationService'
import type { PredictionHistoryEntry } from '@/types/history'

interface HistoryTableProps {
  entries: PredictionHistoryEntry[]
  expandedId: number | null
  onToggleExplanation: (id: number) => void
}

/** "2026-08-06T09:41:22Z" -> "6 Aug 2026, 09:41", in the reader's own timezone. */
function formatRecordedAt(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * The orchestrator records a raw `perf_counter` delta, so a live row's search time arrives as
 * something like 1873.4241000004112 — sixteen digits of noise that would also blow the column open.
 */
function formatSearchTime(ms: number): string {
  return `${Math.round(ms)} ms`
}

/**
 * Desktop view of the audit trail. Every column is a single scannable value so a long
 * run of predictions can be read down the page; Brain 4's prose is the one field that
 * can't be, so it lives in a detail row the reader opens deliberately.
 */
export function HistoryTable({ entries, expandedId, onToggleExplanation }: HistoryTableProps) {
  return (
    <div className="hidden overflow-x-auto rounded-xl border border-border sm:block">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Recorded prediction runs, newest first</caption>
        <thead className="bg-surface-2 text-xs font-semibold tracking-wide text-muted uppercase">
          <tr>
            <th scope="col" className="px-4 py-3">
              Predicted Part
            </th>
            <th scope="col" className="px-4 py-3">
              Confidence
            </th>
            <th scope="col" className="px-4 py-3">
              Top Match
            </th>
            <th scope="col" className="px-4 py-3">
              Candidates
            </th>
            <th scope="col" className="px-4 py-3">
              Model
            </th>
            <th scope="col" className="px-4 py-3">
              Search
            </th>
            <th scope="col" className="px-4 py-3">
              Recorded
            </th>
            <th scope="col" className="px-4 py-3 text-right">
              <span className="sr-only">AI explanation</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {entries.map((entry) => {
            const isExpanded = expandedId === entry.id
            return (
              <Fragment key={entry.id}>
                <tr className="text-foreground">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {entry.thumbnail ? (
                        <img
                          src={entry.thumbnail}
                          alt={`Uploaded photo identified as ${entry.category}`}
                          className="h-12 w-12 shrink-0 rounded-lg border border-border-strong bg-surface-2 object-cover"
                        />
                      ) : (
                        <PartIllustration
                          category={entry.category}
                          className="h-12 w-12 shrink-0 rounded-lg border border-border-strong"
                        />
                      )}
                      <span className="font-medium whitespace-nowrap">{entry.category}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <ConfidenceGauge
                      value={entry.confidence}
                      size={40}
                      tone={entry.confidence >= HIGH_CONFIDENCE_THRESHOLD ? 'success' : 'accent'}
                      label={`Category confidence for the ${entry.category} run`}
                    />
                  </td>
                  <td className="px-4 py-3">
                    {entry.topSku ? (
                      <span className="font-mono text-muted">{entry.topSku}</span>
                    ) : (
                      <StatusBadge variant="warning">No match</StatusBadge>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-muted">{entry.candidates.length}</td>
                  <td className="px-4 py-3">
                    {entry.embeddingBackend ? (
                      <span className="rounded-full border border-border-strong bg-surface-2 px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wide text-subtle uppercase">
                        {entry.embeddingBackend}
                      </span>
                    ) : (
                      <span className="font-mono text-muted">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono whitespace-nowrap text-muted">{formatSearchTime(entry.searchTimeMs)}</td>
                  <td className="px-4 py-3 font-mono whitespace-nowrap text-muted">{formatRecordedAt(entry.createdAt)}</td>
                  <td className="px-4 py-3 text-right">
                    {entry.explanation ? (
                      <button
                        type="button"
                        onClick={() => onToggleExplanation(entry.id)}
                        aria-expanded={isExpanded}
                        aria-controls={isExpanded ? `history-explanation-${entry.id}` : undefined}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-border-strong px-3 py-2 text-xs font-semibold text-foreground transition-colors hover:border-accent/50 hover:text-accent-hover"
                      >
                        <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                        {isExpanded ? 'Hide' : 'Show'}
                        <span className="sr-only"> AI explanation for the {entry.category} run</span>
                      </button>
                    ) : (
                      <span className="font-mono text-subtle">—</span>
                    )}
                  </td>
                </tr>

                {isExpanded && entry.explanation && (
                  <tr className="bg-surface-2/40">
                    <td colSpan={8} className="px-4 py-4">
                      <p
                        id={`history-explanation-${entry.id}`}
                        className="border-l-2 border-accent/30 pl-3 text-sm leading-relaxed whitespace-pre-line text-foreground/90"
                      >
                        {entry.explanation}
                      </p>
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
