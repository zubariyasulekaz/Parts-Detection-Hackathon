import { Loader2, Sparkles, Trash2 } from 'lucide-react'
import { ConfidenceGauge } from '@/components/common/ConfidenceGauge'
import { PartIllustration } from '@/components/common/PartIllustration'
import { ProductThumbnail } from '@/components/common/ProductThumbnail'
import { StatusBadge } from '@/components/common/StatusBadge'
import { HIGH_CONFIDENCE_THRESHOLD } from '@/services/identificationService'
import type { PredictionHistoryEntry } from '@/types/history'

interface HistoryEntryCardProps {
  entry: PredictionHistoryEntry
  isExpanded: boolean
  /** Catalog photo of the SKU this run matched, when the catalog has one. */
  matchedSkuImage?: string
  isDeleting: boolean
  onToggleExplanation: () => void
  onDelete: () => void
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

/** Same rounding HistoryTable applies - a live row's search time is an unrounded `perf_counter` delta. */
function formatSearchTime(ms: number): string {
  return `${Math.round(ms)} ms`
}

/** One recorded run at phone width, where HistoryTable's eight columns can't fit. */
export function HistoryEntryCard({
  entry,
  isExpanded,
  matchedSkuImage,
  isDeleting,
  onToggleExplanation,
  onDelete,
}: HistoryEntryCardProps) {
  return (
    <article className="shadow-card flex flex-col gap-3 rounded-xl border border-border bg-surface p-4">
      <div className="flex items-start gap-3">
        {entry.thumbnail ? (
          <img
            src={entry.thumbnail}
            alt={`Uploaded photo identified as ${entry.category}`}
            className="h-14 w-14 shrink-0 rounded-lg border border-border-strong bg-surface-2 object-cover"
          />
        ) : (
          <PartIllustration category={entry.category} className="h-14 w-14 shrink-0 rounded-lg border border-border-strong" />
        )}

        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-foreground">{entry.category}</p>
          {entry.topSku ? (
            <span className="mt-1 flex flex-wrap items-center gap-2">
              <ProductThumbnail
                category={entry.category}
                images={matchedSkuImage ? [matchedSkuImage] : []}
                className="h-8 w-8 shrink-0 rounded-md border border-border-strong"
              />
              <span className="font-mono text-xs text-subtle">{entry.topSku}</span>
              {entry.confirmedSku &&
                (entry.confirmedSku === entry.topSku ? (
                  <StatusBadge variant="success">Confirmed</StatusBadge>
                ) : (
                  <StatusBadge variant="warning">Corrected → {entry.confirmedSku}</StatusBadge>
                ))}
            </span>
          ) : (
            <StatusBadge variant="warning" className="mt-1">
              No match
            </StatusBadge>
          )}
          <p className="mt-1 font-mono text-xs text-subtle">{formatRecordedAt(entry.createdAt)}</p>
        </div>

        <ConfidenceGauge
          value={entry.confidence}
          size={40}
          tone={entry.confidence >= HIGH_CONFIDENCE_THRESHOLD ? 'success' : 'accent'}
          label={`Category confidence for the ${entry.category} run`}
        />
      </div>

      <dl className="grid grid-cols-2 gap-2 border-t border-border pt-3">
        <div>
          <dt className="text-xs font-semibold tracking-wide text-subtle uppercase">Search</dt>
          <dd className="mt-0.5 font-mono text-xs text-muted">{formatSearchTime(entry.searchTimeMs)}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold tracking-wide text-subtle uppercase">Model</dt>
          <dd className="mt-0.5 font-mono text-xs text-muted uppercase">{entry.embeddingBackend ?? '-'}</dd>
        </div>
      </dl>

      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          {entry.explanation && (
            <button
              type="button"
              onClick={onToggleExplanation}
              aria-expanded={isExpanded}
              aria-controls={isExpanded ? `history-explanation-card-${entry.id}` : undefined}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border-strong px-3 py-2 text-xs font-semibold text-foreground transition-colors hover:border-accent/50 hover:text-accent-hover"
            >
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              {/* Spelt out on the card: unlike the table there is no column
                  header here to tell the reader what "Show" would show. */}
              {isExpanded ? 'Hide' : 'Show'} explanation
              <span className="sr-only"> for the {entry.category} run</span>
            </button>
          )}
          <button
            type="button"
            onClick={onDelete}
            disabled={isDeleting}
            className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-border-strong px-3 py-2 text-xs font-semibold text-muted transition-colors hover:border-danger/50 hover:text-danger disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isDeleting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            ) : (
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            Delete
            <span className="sr-only"> the {entry.category} run recorded {formatRecordedAt(entry.createdAt)}</span>
          </button>
        </div>

        {isExpanded && entry.explanation && (
          <p
            id={`history-explanation-card-${entry.id}`}
            className="border-l-2 border-accent/30 pl-3 text-sm leading-relaxed whitespace-pre-line text-foreground/90"
          >
            {entry.explanation}
          </p>
        )}
      </div>
    </article>
  )
}
