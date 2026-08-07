import { StatusBadge } from '@/components/common/StatusBadge'
import { formatPercent } from '@/utils/format'
import type { CategoryPrediction, IdentificationCandidate } from '@/types/identification'
import { ConfidenceMetric } from './ConfidenceMetric'

interface IdentificationSummaryProps {
  category: CategoryPrediction
  selectedCandidate: IdentificationCandidate | null
  isHighConfidence: boolean
  onViewProduct: () => void
  onConfirmMatch: () => void
}

export function IdentificationSummary({
  category,
  selectedCandidate,
  isHighConfidence,
  onViewProduct,
  onConfirmMatch,
}: IdentificationSummaryProps) {
  return (
    // Sits full-width beneath the image comparison, so the metrics, product and
    // actions read as one horizontal summary bar rather than a tall column.
    <div className="shadow-card flex flex-col gap-5 rounded-xl border border-border bg-surface p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="heading-eyebrow text-sm font-bold tracking-wide text-muted uppercase">Best Catalog Match</h2>
        {isHighConfidence && selectedCandidate && (
          <StatusBadge variant="success">High-confidence identification</StatusBadge>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,14rem)_minmax(0,14rem)_1fr] lg:items-center">
        <ConfidenceMetric
          label="Category Prediction"
          primary={category.name}
          secondary={`${formatPercent(category.confidence)} confidence`}
          gaugeValue={category.confidence}
          gaugeTone={isHighConfidence ? 'success' : 'accent'}
        />
        {selectedCandidate ? (
          <ConfidenceMetric
            label="Catalog Match"
            primary={selectedCandidate.sku}
            primaryMono
            secondary={`${formatPercent(selectedCandidate.similarity)} visual similarity`}
            gaugeValue={selectedCandidate.similarity}
            gaugeTone={isHighConfidence ? 'success' : 'accent'}
          />
        ) : (
          <div>
            <p className="text-xs font-semibold tracking-wide text-muted uppercase">Catalog Match</p>
            <p className="mt-1 text-sm text-subtle">Awaiting confirmation below</p>
          </div>
        )}

        {selectedCandidate && (
          <div className="rounded-lg border border-border-strong bg-surface-2 p-4">
            <p className="text-xs font-semibold tracking-wide text-muted uppercase">{selectedCandidate.brand}</p>
            <p className="text-base font-semibold text-foreground">{selectedCandidate.productName}</p>
            <p className="text-xs text-subtle">{selectedCandidate.category}</p>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-3 pt-1 sm:flex-row sm:justify-end">
        <button
          type="button"
          onClick={onConfirmMatch}
          disabled={!selectedCandidate}
          className="shadow-glow-accent rounded-lg bg-linear-to-b from-accent-hover to-accent px-6 py-2.5 text-sm font-semibold text-white transition-transform sm:w-48 hover:-translate-y-0.5 active:translate-y-0 disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
        >
          Confirm Match
        </button>
        <button
          type="button"
          onClick={onViewProduct}
          disabled={!selectedCandidate}
          className="rounded-lg border border-border-strong px-6 py-2.5 sm:w-48 text-sm font-semibold text-foreground transition-colors hover:border-accent/50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          View Product
        </button>
      </div>
    </div>
  )
}
