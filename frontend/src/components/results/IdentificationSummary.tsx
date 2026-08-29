import { CircleCheck, TriangleAlert } from 'lucide-react'
import { StatusBadge } from '@/components/common/StatusBadge'
import type { VisualMismatch } from '@/services/disambiguation'
import { formatPercent } from '@/utils/format'
import type { IdentificationCandidate } from '@/types/identification'
import type { VehicleCompatibility } from '@/types/product'

interface IdentificationSummaryProps {
  selectedCandidate: IdentificationCandidate | null
  /** Brain 1's category confidence, e.g. "is this even a Shock Absorber" - drives only the header badge. */
  isHighConfidence: boolean
  /** True when this candidate is the photo's own decisive pick, clearly ahead of the rest - drives the match reasoning below, independent of the category badge. */
  isDecisiveMatch: boolean
  /** How many guided questions were answered - used only for the "N answers" wording, not to decide the tone. */
  answeredQuestions: number
  /** True when the current pick is what the answer trail actually narrowed down to (not just "some answers exist"). */
  confirmedByAnswers: boolean
  /** Set when the answer trail ruled out the candidate the photo itself most strongly favored. */
  mismatch: VisualMismatch | null
  onConfirmMatch: () => void
}

/** `[{make: 'Ford', model: 'F-150', ...}, ...]` -> "Ford F-150 (2015-2020) +2 more". */
function fitmentSummary(vehicles: VehicleCompatibility[]): string | null {
  if (vehicles.length === 0) return null
  const [first, ...rest] = vehicles
  const label = `${first.make} ${first.model} (${first.yearStart}–${first.yearEnd})`
  return rest.length > 0 ? `${label} +${rest.length} more` : label
}

interface MatchReason {
  tone: 'positive' | 'caution'
  text: string
}

/**
 * Why this candidate, in one sentence - the thing a bare "Confirm Match"
 * button never told the user. Combines the same signals the guided flow
 * uses (answers, visual similarity, mismatch) rather than presenting
 * whichever one happens to be selected as self-evidently correct.
 *
 * Deliberately keyed on this candidate's own similarity/separation, not
 * Brain 1's category confidence (a 98% visual match shouldn't read as
 * unconfirmed just because the classifier was unsure of the category, and a
 * weak match shouldn't borrow the classifier's confidence either) - and on
 * whether the *current* pick is actually what the answers resolved to, not
 * just "some answers were given somewhere in this session". The candidate
 * grid keeps ruled-out cards clickable, so a manual pick after answering can
 * be a candidate the answers themselves excluded.
 */
function matchReason(
  candidate: IdentificationCandidate,
  isDecisiveMatch: boolean,
  answeredQuestions: number,
  confirmedByAnswers: boolean,
  mismatch: VisualMismatch | null,
): MatchReason {
  if (mismatch && candidate.sku === mismatch.bestSurvivor.sku) {
    // The full comparison and the "use this one instead?" choice already
    // live in the guided questions above - repeating the numbers here would
    // just say the same thing twice.
    return {
      tone: 'caution',
      text: 'Visual mismatch flagged above - resolve it there before confirming.',
    }
  }
  if (confirmedByAnswers) {
    const answers = `${answeredQuestions} answer${answeredQuestions === 1 ? '' : 's'}`
    // An answer narrows the shortlist; it does not check that the shortlist
    // contained the right part. When the photo match is weak, claiming
    // "confirmed" turns a guess into a certainty - seen on a wiring connector
    // matched at 31% with a one-point lead, presented as confirmed. If the
    // right product was never in the candidates, the answer only picked the
    // wrong one more confidently.
    if (!isDecisiveMatch) {
      return {
        tone: 'caution',
        text: `Narrowed to this one by your ${answers} - but the photo itself is a weak match `
          + `(${formatPercent(candidate.similarity)}, close to the others). Check the picture `
          + `carefully, or say none of these is your part.`,
      }
    }
    return {
      tone: 'positive',
      text: `Confirmed by ${answers} you gave above, and the photo's own clear best match.`,
    }
  }
  if (isDecisiveMatch) {
    return {
      tone: 'positive',
      text: `${formatPercent(candidate.similarity)} visual similarity to your photo, clearly ahead of every other candidate - no clarifying questions were needed.`,
    }
  }
  return {
    tone: 'caution',
    text: `${formatPercent(candidate.similarity)} visual similarity, but it isn't the photo's clear best match or confirmed by your answers. Compare the candidates below if this isn't right.`,
  }
}

/**
 * The one action-bearing card on the page: explains why this candidate is
 * the pick (not just that it is one) and is the only path to
 * `onConfirmMatch`. Deliberately doesn't repeat the similarity gauge already
 * shown in the hero comparison figure above it - a second gauge for the
 * same number added noise, not signal. One button, not two: "view without
 * confirming" vs. "confirm and view" was a distinction only the audit trail
 * cared about, not the person clicking it.
 */
export function IdentificationSummary({
  selectedCandidate,
  isHighConfidence,
  isDecisiveMatch,
  answeredQuestions,
  confirmedByAnswers,
  mismatch,
  onConfirmMatch,
}: IdentificationSummaryProps) {
  const reason = selectedCandidate
    ? matchReason(selectedCandidate, isDecisiveMatch, answeredQuestions, confirmedByAnswers, mismatch)
    : null
  const fitment = selectedCandidate ? fitmentSummary(selectedCandidate.compatibleVehicles) : null

  return (
    <div className="shadow-card flex flex-col gap-5 rounded-xl border border-border bg-surface p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="heading-eyebrow text-sm font-bold tracking-wide text-muted uppercase">Your Match</h2>
        {isHighConfidence && selectedCandidate && (
          <StatusBadge variant="success">High-confidence identification</StatusBadge>
        )}
      </div>

      {selectedCandidate ? (
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2 rounded-lg border border-border-strong bg-surface-2 p-4 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
            <div>
              <p className="text-xs font-semibold tracking-wide text-muted uppercase">{selectedCandidate.brand}</p>
              <p className="text-base font-semibold text-foreground">{selectedCandidate.productName}</p>
              <p className="font-mono text-xs text-subtle">
                {selectedCandidate.sku} · {selectedCandidate.category}
              </p>
            </div>
            <p className="font-mono text-sm font-bold text-foreground sm:text-right">
              {formatPercent(selectedCandidate.similarity)}
              <span className="ml-1.5 block text-xs font-normal text-subtle sm:mt-0.5">visual match</span>
            </p>
          </div>

          {/* Why this pick, and whether it actually fits the user's vehicle -
              the two things "Confirm Match" alone never answered. */}
          <div className="flex flex-col gap-2">
            {reason && (
              <p className="flex items-start gap-2 text-sm text-muted">
                {reason.tone === 'positive' ? (
                  <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-success" aria-hidden="true" />
                ) : (
                  <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden="true" />
                )}
                <span>{reason.text}</span>
              </p>
            )}
            {fitment ? (
              reason?.tone === 'caution' ? (
                // The pick itself isn't confirmed yet, so a confident green
                // "Fits X" checkmark here would contradict the caution line
                // above it - this is catalog fitment for the SKU, not a
                // verified match to the user's actual vehicle.
                <p className="flex items-start gap-2 text-sm text-muted">
                  <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden="true" />
                  <span>
                    Catalog listing covers <span className="font-semibold text-foreground">{fitment}</span> - not
                    yet confirmed as your vehicle.
                  </span>
                </p>
              ) : (
                <p className="flex items-start gap-2 text-sm text-muted">
                  <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-success" aria-hidden="true" />
                  <span>
                    Fits <span className="font-semibold text-foreground">{fitment}</span>
                  </span>
                </p>
              )
            ) : (
              <p className="flex items-start gap-2 text-sm text-muted">
                <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden="true" />
                <span>No fitment on record for this SKU - verify it suits your vehicle before ordering.</span>
              </p>
            )}
          </div>
        </div>
      ) : (
        <p className="text-sm text-subtle">Awaiting confirmation above.</p>
      )}

      <div className="flex justify-end pt-1">
        <button
          type="button"
          onClick={onConfirmMatch}
          disabled={!selectedCandidate}
          className="shadow-glow-accent w-full rounded-lg bg-linear-to-b from-accent-hover to-accent px-8 py-3 text-sm font-semibold text-white transition-transform sm:w-auto hover:-translate-y-0.5 active:translate-y-0 disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
        >
          View Product
        </button>
      </div>
    </div>
  )
}
