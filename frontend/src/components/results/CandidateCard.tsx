import { CircleCheck } from 'lucide-react'
import { ConfidenceGauge } from '@/components/common/ConfidenceGauge'
import { ProductThumbnail } from '@/components/common/ProductThumbnail'
import { Tilt3D } from '@/components/common/Tilt3D'
import { formatPercent } from '@/utils/format'
import type { IdentificationCandidate } from '@/types/identification'

interface CandidateCardProps {
  candidate: IdentificationCandidate
  isSelected: boolean
  isPrimaryAction: boolean
  /**
   * Entitled to the "Best Match" badge - a clear leader, not merely rank 1.
   * Decided by `confidentLeader`, so the badge and the summary's wording
   * cannot contradict each other.
   */
  isBestMatch?: boolean
  /** Eliminated by an answer in the guided flow. Still selectable - the user may know better. */
  isRuledOut?: boolean
  onSelect: () => void
}

/** `"friction_material"` -> `"Friction material"`. */
function attributeLabel(key: string): string {
  const spaced = key.replace(/[_-]+/g, ' ')
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

export function CandidateCard({
  candidate,
  isSelected,
  isPrimaryAction,
  isBestMatch = false,
  isRuledOut = false,
  onSelect,
}: CandidateCardProps) {
  // The facts that tell look-alike candidates apart - the same data the
  // guided questions ask about. Shown on the card so "what's actually
  // different?" has a visible answer instead of a hidden one.
  const attributeChips = Object.entries(candidate.attributes ?? {}).slice(0, 3)

  return (
    // The inner button is the single interactive control (keyboard +
    // screen readers); this wrapper only widens the mouse click target.
    // A role="button" here would nest interactive controls, which
    // assistive tech announces as one broken widget.
    //
    // `near` perspective: at a grid card's size the hero's 1200px camera
    // makes the same tilt angle read as a flat skew. The old
    // `hover:-translate-y-0.5` is gone - the tilt's own `--tilt-lift`
    // is the lift now, and two competing transforms fought each other.
    <Tilt3D
      onClick={onSelect}
      intensity="subtle"
      near
      glare
      sceneClassName="h-full"
      className={`shadow-depth group flex h-full cursor-pointer flex-col overflow-hidden rounded-xl border bg-surface ${
        isSelected ? 'shadow-glow-accent border-accent' : 'border-border-strong hover:shadow-depth-lift'
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
          {/* Not `rank === 1`: that fires on every search, including the ones
              where the top three are a point apart and the leader is a coin
              toss. A parts counter reads the badge, not the percentage. */}
          {isBestMatch && (
            <span className="shadow-glow-accent rounded-full bg-accent px-2 py-0.5 text-xs font-bold tracking-wide text-white uppercase">
              Best Match
            </span>
          )}
          <span className="rounded-full bg-surface/90 px-2 py-0.5 font-mono text-xs font-semibold text-muted backdrop-blur">
            RANK #{candidate.rank}
          </span>
          {isRuledOut && (
            <span className="rounded-full bg-surface/90 px-2 py-0.5 text-xs font-bold tracking-wide text-warning-soft uppercase backdrop-blur">
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

        {(candidate.manufacturerPartNumber || attributeChips.length > 0) && (
          <ul className="mt-1.5 flex flex-wrap gap-1.5">
            {candidate.manufacturerPartNumber && (
              <li className="rounded-md border border-border-strong bg-surface-2 px-1.5 py-0.5 font-mono text-xs text-muted">
                MPN {candidate.manufacturerPartNumber}
              </li>
            )}
            {attributeChips.map(([key, value]) => (
              <li
                key={key}
                className="rounded-md border border-border-strong bg-surface-2 px-1.5 py-0.5 text-xs text-muted"
                title={attributeLabel(key)}
              >
                {value}
              </li>
            ))}
          </ul>
        )}

        <div className="mt-2 flex items-center gap-3">
          <ConfidenceGauge value={candidate.similarity} size={40} tone={isSelected ? 'success' : 'accent'} label="Visual similarity" />
          <div>
            <p className="font-mono text-sm font-bold text-foreground">{formatPercent(candidate.similarity)}</p>
            <p className="text-xs text-subtle">Visual similarity</p>
          </div>
        </div>

        <button
          type="button"
          aria-pressed={isSelected}
          aria-label={`Select ${candidate.productName}, SKU ${candidate.sku}, rank ${candidate.rank}, ${formatPercent(candidate.similarity)} visual similarity`}
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
    </Tilt3D>
  )
}
