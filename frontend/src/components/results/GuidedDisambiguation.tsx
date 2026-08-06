import { Check, CircleHelp, RotateCcw, Sparkles } from 'lucide-react'
import { useMemo, useState } from 'react'
import { StatusBadge } from '@/components/common/StatusBadge'
import {
  applyAnswers,
  nextQuestion,
  type DisambiguationAnswer,
  type FacetKey,
} from '@/services/disambiguation'
import type { IdentificationCandidate } from '@/types/identification'

interface GuidedDisambiguationProps {
  candidates: IdentificationCandidate[]
  /** Called as the set narrows, so the candidate grid can rule cards out in step. */
  onRemainingChange: (skus: string[]) => void
  /** Called when exactly one candidate is left — the answer to the whole flow. */
  onResolved: (sku: string) => void
}

const FACET_LABEL: Record<string, string> = {
  make: 'Vehicle',
  model: 'Model',
  year: 'Year',
  mpn: 'Part number',
  brand: 'Brand',
}

/** `attr:filter_style` -> "Filter style"; anything else falls back to the map. */
function facetLabel(facet: FacetKey): string {
  if (!facet.startsWith('attr:')) return FACET_LABEL[facet] ?? facet
  const key = facet.slice('attr:'.length).replace(/[_-]+/g, ' ')
  return key.charAt(0).toUpperCase() + key.slice(1)
}

/**
 * Asks the user what the photo cannot tell us.
 *
 * When candidates are within a few points of each other, comparing thumbnails is
 * a coin flip — they look alike because they are the same shape. The catalog
 * knows what actually differs (which car it fits, who made it), so this walks
 * through those facts one chip-picker at a time, the way a parts counter would.
 */
export function GuidedDisambiguation({
  candidates,
  onRemainingChange,
  onResolved,
}: GuidedDisambiguationProps) {
  const [answers, setAnswers] = useState<DisambiguationAnswer[]>([])
  const [skipped, setSkipped] = useState<FacetKey[]>([])

  const remaining = useMemo(() => applyAnswers(candidates, answers), [candidates, answers])
  // nextQuestion applies the answers itself — it needs the full candidate list
  // so it can narrow the fitment rows in step with them.
  const question = useMemo(
    () => nextQuestion(candidates, answers, skipped),
    [candidates, answers, skipped],
  )
  const resolved = remaining.length === 1 ? remaining[0] : null

  function answer(option: DisambiguationAnswer) {
    const next = [...answers, option]
    setAnswers(next)
    const left = applyAnswers(candidates, next)
    onRemainingChange(left.map((candidate) => candidate.sku))
    if (left.length === 1) onResolved(left[0].sku)
  }

  function undo(index: number) {
    const next = answers.slice(0, index)
    setAnswers(next)
    setSkipped([])
    onRemainingChange(applyAnswers(candidates, next).map((candidate) => candidate.sku))
  }

  function restart() {
    setAnswers([])
    setSkipped([])
    onRemainingChange(candidates.map((candidate) => candidate.sku))
  }

  return (
    <section
      aria-label="Narrow down the match"
      className="shadow-card flex flex-col gap-4 rounded-xl border border-accent/25 bg-surface p-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent/15 text-accent-soft">
            <Sparkles className="h-4 w-4" aria-hidden="true" />
          </span>
          <h2 className="text-sm font-bold text-foreground">Let&rsquo;s narrow it down</h2>
        </div>
        <StatusBadge variant={resolved ? 'success' : 'info'}>
          {resolved ? '1 match' : `${remaining.length} possible matches`}
        </StatusBadge>
      </div>

      {/* Answered questions stay visible and reversible — a wrong tap early on
          would otherwise silently decide the whole result. */}
      {answers.length > 0 && (
        <ol className="flex flex-col gap-2">
          {answers.map((entry, index) => (
            <li key={`${entry.facet}-${entry.label}`} className="flex items-center gap-2 text-sm">
              <Check className="h-4 w-4 shrink-0 text-success" aria-hidden="true" />
              <span className="text-muted">{facetLabel(entry.facet)}:</span>
              <span className="font-semibold text-foreground">{entry.label}</span>
              <button
                type="button"
                onClick={() => undo(index)}
                className="ml-auto inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold text-subtle transition-colors hover:text-accent-hover"
              >
                <RotateCcw className="h-3 w-3" aria-hidden="true" />
                Change
                <span className="sr-only"> your {facetLabel(entry.facet)} answer</span>
              </button>
            </li>
          ))}
        </ol>
      )}

      {resolved ? (
        <div className="rounded-lg border border-success/30 bg-success-muted/40 p-4">
          <p className="text-sm text-foreground">
            That leaves one match:{' '}
            <span className="font-mono font-semibold">{resolved.sku}</span> —{' '}
            <span className="font-semibold">{resolved.productName}</span>
          </p>
          <p className="mt-1 text-xs text-muted">
            Selected below. Change any answer above if that doesn&rsquo;t look right.
          </p>
        </div>
      ) : question ? (
        <div className="flex flex-col gap-3">
          <div className="rounded-lg rounded-tl-sm border border-border-strong bg-surface-2 px-4 py-3">
            <p className="text-sm font-semibold text-foreground">{question.prompt}</p>
            <p className="mt-0.5 text-xs text-muted">{question.hint}</p>
          </div>

          <div className="flex flex-wrap gap-2">
            {question.options.map((option) => (
              <button
                key={option.label}
                type="button"
                onClick={() =>
                  answer({
                    facet: question.facet,
                    label: option.label,
                    skus: option.skus,
                    filter: option.filter,
                  })
                }
                className="rounded-full border border-border-strong bg-surface-2 px-4 py-2 text-sm font-semibold text-foreground transition-colors hover:border-accent hover:bg-accent/10 hover:text-accent-soft"
              >
                {option.label}
                <span className="ml-1.5 font-mono text-[11px] font-normal text-subtle">
                  {option.skus.length}
                </span>
              </button>
            ))}
            <button
              type="button"
              onClick={() => setSkipped((current) => [...current, question.facet])}
              className="inline-flex items-center gap-1.5 rounded-full px-3 py-2 text-sm font-medium text-subtle transition-colors hover:text-foreground"
            >
              <CircleHelp className="h-4 w-4" aria-hidden="true" />
              Not sure
            </button>
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-border-strong bg-surface-2 p-4">
          <p className="text-sm text-foreground">
            {remaining.length} candidates are still possible, and the catalog has nothing further
            that tells them apart.
          </p>
          <p className="mt-1 text-xs text-muted">
            Compare the photos below and pick the one that matches your part.
          </p>
          {answers.length > 0 && (
            <button
              type="button"
              onClick={restart}
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-border-strong px-3 py-1.5 text-xs font-semibold text-foreground transition-colors hover:border-accent/50"
            >
              <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
              Start over
            </button>
          )}
        </div>
      )}
    </section>
  )
}
