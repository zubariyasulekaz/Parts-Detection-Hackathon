import { CircleCheck } from 'lucide-react'
import type { KeyboardEvent } from 'react'
import { ConfidenceGauge } from '@/components/common/ConfidenceGauge'
import { ProductThumbnail } from '@/components/common/ProductThumbnail'
import { formatPercent } from '@/utils/format'
import type { IdentificationCandidate } from '@/types/identification'

interface CandidateCardProps {
  candidate: IdentificationCandidate
  isSelected: boolean
  isPrimaryAction: boolean
  /** False when no candidate cleared the match threshold — calling rank 1 the "best match" would overstate it. */
  showBestMatch?: boolean
  /** Eliminated by an answer in the guided flow. Still selectable — the user may know better. */
  isRuledOut?: boolean
  onSelect: () => void
}

export function CandidateCard({
  candidate,
  isSelected,
  isPrimaryAction,
  showBestMatch = true,
  isRuledOut = false,
  onSelect,
}: CandidateCardProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onSelect()
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-pressed={isSelected}
      aria-label={`${candidate.productName}, SKU ${candidate.sku}, rank ${candidate.rank}, ${formatPercent(candidate.similarity)} visual similarity`}
      onClick={onSelect}
      onKeyDown={handleKeyDown}
      className={`shadow-card group flex flex-col overflow-hidden rounded-xl border bg-surface transition-all hover:-translate-y-0.5 ${
        isSelected ? 'shadow-glow-accent border-accent' : 'border-border-strong hover:shadow-glow-accent'
      }`}
    >
      <div className="relative aspect-4/3">
        <ProductThumbnail
          category={candidate.category}
          images={candidate.imageUrl ? [candidate.imageUrl] : []}
          fit="cover"
          className="h-full w-full"
        />
        <div className="absolute top-2.5 left-2.5 flex gap-1.5">
          {showBestMatch && candidate.rank === 1 && (
            <span className="shadow-glow-accent rounded-full bg-accent px-2 py-0.5 text-[11px] font-bold tracking-wide text-white uppercase">
              Best Match
            </span>
          )}
          <span className="rounded-full bg-surface/90 px-2 py-0.5 font-mono text-[11px] font-semibold text-muted backdrop-blur">
            RANK #{candidate.rank}
          </span>
          {isRuledOut && (
            <span className="rounded-full bg-surface/90 px-2 py-0.5 text-[11px] font-bold tracking-wide text-warning-soft uppercase backdrop-blur">
              Ruled out
            </span>
          )}
        </div>
        {isSelected && (
          <span className="absolute top-2.5 right-2.5 flex h-6 w-6 items-center justify-center rounded-full bg-accent text-white">
            <CircleCheck className="h-4 w-4" aria-hidden="true" />
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-1 p-4 text-left">
        <span className="text-xs font-semibold tracking-wide text-muted uppercase">{candidate.brand}</span>
        <span className="text-sm font-semibold text-foreground">{candidate.productName}</span>
        <span className="font-mono text-xs text-subtle">
          {candidate.sku} · {candidate.category}
        </span>

        <div className="mt-2 flex items-center gap-3">
          <ConfidenceGauge value={candidate.similarity} size={40} tone={isSelected ? 'success' : 'accent'} label="Visual similarity" />
          <div>
            <p className="font-mono text-sm font-bold text-foreground">{formatPercent(candidate.similarity)}</p>
            <p className="text-[11px] text-subtle">Visual similarity</p>
          </div>
        </div>

        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation()
            onSelect()
          }}
          className={`mt-3 rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${
            isSelected
              ? 'border border-accent/40 text-accent-hover'
              : isPrimaryAction
                ? 'bg-accent text-white hover:bg-accent-hover'
                : 'border border-border-strong text-foreground hover:border-accent/50'
          }`}
        >
          {isSelected ? 'Selected' : 'Select This Product'}
        </button>
      </div>
    </div>
  )
}
