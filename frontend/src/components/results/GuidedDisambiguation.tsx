import { CircleHelp, RotateCcw, SkipForward, Sparkles, TriangleAlert } from 'lucide-react'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { StatusBadge } from '@/components/common/StatusBadge'
import {
  applyAnswers,
  detectVisualMismatch,
  nextQuestion,
  promptFor,
  type DisambiguationAnswer,
  type FacetKey,
} from '@/services/disambiguation'
import { formatPercent } from '@/utils/format'
import type { IdentificationCandidate } from '@/types/identification'

interface GuidedDisambiguationProps {
  candidates: IdentificationCandidate[]
  /** Called as the set narrows, so the candidate grid can rule cards out in step. */
  onRemainingChange: (skus: string[]) => void
  /** Called when exactly one candidate is left - the answer to the whole flow. */
  onResolved: (sku: string, answers: DisambiguationAnswer[]) => void
  /** Kept in sync with the answer trail, so a later "Confirm Match" can report how the pick was reached. */
  onAnswersChange?: (answers: DisambiguationAnswer[]) => void
  /**
   * Called once there is nothing left to ask - resolved to one candidate, out
   * of useful questions, or the user skipped ahead. The results page treats
   * this as the go-ahead to reveal product images.
   */
  onFinished?: (remainingSkus: string[]) => void
  /**
   * Lets the user swap the answer-derived pick for the candidate their photo
   * actually favors (or back again) when the two disagree - see `mismatch`
   * below. The results page wires this straight to its own selection state.
   */
  onOverrideSelection?: (sku: string) => void
  /** The results page's current pick, so the mismatch choice can show which side is currently active. */
  selectedSku?: string | null
}

/** One message in the narrowing conversation - PartPilot asking on the left, the user's pick on the right. */
function ChatBubble({
  side,
  tone = 'default',
  children,
}: {
  side: 'left' | 'right'
  tone?: 'default' | 'success' | 'caution'
  children: ReactNode
}) {
  return (
    <div className={`flex ${side === 'left' ? 'justify-start' : 'justify-end'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${side === 'left' ? 'rounded-bl-sm' : 'rounded-br-sm'} ${
          side === 'right'
            ? 'bg-accent text-white'
            : tone === 'success'
              ? 'border border-success/30 bg-success-muted/40'
              : tone === 'caution'
                ? 'border border-warning/30 bg-warning-muted/40'
                : 'border border-border-strong bg-surface-2'
        }`}
      >
        {children}
      </div>
    </div>
  )
}

/**
 * Asks the user what the photo cannot tell us, as a chat thread.
 *
 * When candidates are within a few points of each other, comparing thumbnails is
 * a coin flip - they look alike because they are the same shape. The catalog
 * knows what actually differs (which car it fits, who made it), so this walks
 * through those facts one question at a time, the way a parts counter would -
 * PartPilot's question on the left, the user's answer on the right.
 */
export function GuidedDisambiguation({
  candidates,
  onRemainingChange,
  onResolved,
  onAnswersChange,
  onFinished,
  onOverrideSelection,
  selectedSku = null,
}: GuidedDisambiguationProps) {
  const [answers, setAnswers] = useState<DisambiguationAnswer[]>([])
  const [skipped, setSkipped] = useState<FacetKey[]>([])
  // The user chose "show me the matches" - stop asking regardless of what
  // nextQuestion would offer next.
  const [skippedAll, setSkippedAll] = useState(false)

  const remaining = useMemo(() => applyAnswers(candidates, answers), [candidates, answers])
  // nextQuestion applies the answers itself - it needs the full candidate list
  // so it can narrow the fitment rows in step with them.
  const question = useMemo(
    () => (skippedAll ? null : nextQuestion(candidates, answers, skipped)),
    [candidates, answers, skipped, skippedAll],
  )
  const resolved = remaining.length === 1 ? remaining[0] : null
  // Whether the answers given so far have ruled out the candidate the photo
  // itself most strongly favored - re-derived every render (never its own
  // state) so undoing the answer that caused it clears it automatically.
  const mismatch = useMemo(() => detectVisualMismatch(candidates, answers), [candidates, answers])
  const isMismatchedResolution = Boolean(resolved && mismatch && resolved.sku === mismatch.bestSurvivor.sku)

  // Resolved to one, or nothing left worth asking (naturally or because the
  // user skipped ahead) - either way the caller can now reveal images.
  useEffect(() => {
    if (resolved || !question) onFinished?.(remaining.map((candidate) => candidate.sku))
  }, [resolved, question, remaining, onFinished])

  function answer(option: DisambiguationAnswer) {
    const next = [...answers, option]
    setAnswers(next)
    onAnswersChange?.(next)
    const left = applyAnswers(candidates, next)
    onRemainingChange(left.map((candidate) => candidate.sku))
    if (left.length === 1) onResolved(left[0].sku, next)
  }

  function undo(index: number) {
    const next = answers.slice(0, index)
    setAnswers(next)
    onAnswersChange?.(next)
    setSkipped([])
    onRemainingChange(applyAnswers(candidates, next).map((candidate) => candidate.sku))
  }

  function restart() {
    setAnswers([])
    onAnswersChange?.([])
    setSkipped([])
    setSkippedAll(false)
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

      <div className="flex flex-col gap-2.5">
        {/* Each past question sits on the left, its answer on the right - a
            wrong tap early on stays visible and reversible instead of
            silently deciding the whole result. */}
        {answers.map((entry, index) => (
          <div
            key={`${entry.facet}-${index}`}
            className="grid grid-cols-1 gap-2 rounded-lg border border-border-strong bg-surface-2 p-3.5 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] sm:items-center sm:gap-4"
          >
            <p className="text-sm font-semibold text-foreground">{promptFor(entry.facet).prompt}</p>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-2 rounded-full border border-accent/40 bg-accent/10 px-3 py-1.5 text-sm font-semibold text-accent-soft">
                {entry.label}
              </span>
              <button
                type="button"
                onClick={() => undo(index)}
                aria-label={`Change your answer: ${entry.label}`}
                className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium text-subtle transition-colors hover:text-foreground"
              >
                <RotateCcw className="h-3 w-3" aria-hidden="true" />
                Change
              </button>
            </div>
          </div>
        ))}

        {question && (
          <div className="grid grid-cols-1 gap-2 rounded-lg border border-accent/30 bg-surface p-3.5 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] sm:items-start sm:gap-4">
            <div>
              <p className="text-sm font-semibold text-foreground">{question.prompt}</p>
              {question.hint && <p className="mt-0.5 text-xs text-muted">{question.hint}</p>}
            </div>

            <div className="flex flex-wrap items-center gap-2">
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
                  <span className="ml-1.5 font-mono text-xs font-normal text-subtle">
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
        )}

        {question && (
          <button
            type="button"
            onClick={() => setSkippedAll(true)}
            className="inline-flex w-fit items-center gap-1.5 pl-1 text-xs font-medium text-subtle transition-colors hover:text-foreground"
          >
            <SkipForward className="h-3.5 w-3.5" aria-hidden="true" />
            Skip questions - show me the matches
          </button>
        )}

        {resolved && (
          <ChatBubble side="left" tone={isMismatchedResolution ? 'caution' : 'success'}>
            {isMismatchedResolution && mismatch ? (
              <>
                <p className="mb-1.5 flex items-center gap-1.5 text-xs font-bold text-warning-soft">
                  <TriangleAlert className="h-3.5 w-3.5" aria-hidden="true" />
                  Visual mismatch
                </p>
                <p className="text-sm text-foreground">
                  Based on your answers, this is{' '}
                  <span className="font-mono font-semibold">{resolved.sku}</span> -{' '}
                  <span className="font-semibold">{resolved.productName}</span>. But your uploaded photo is a{' '}
                  <span className="font-semibold text-foreground">{formatPercent(mismatch.visualLeader.similarity)}</span>{' '}
                  visual match for{' '}
                  <span className="font-mono font-semibold text-foreground">{mismatch.visualLeader.sku}</span> instead
                  (this one scores {formatPercent(mismatch.bestSurvivor.similarity)}). Could you verify again, or
                  would this product work for you?
                </p>
                <div className="mt-2.5 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => onOverrideSelection?.(resolved.sku)}
                    aria-pressed={selectedSku === resolved.sku}
                    className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                      selectedSku === resolved.sku
                        ? 'border-warning bg-warning text-white'
                        : 'border-warning/40 bg-surface text-warning-soft hover:bg-warning-muted/40'
                    }`}
                  >
                    Yes, use {resolved.sku}
                  </button>
                  <button
                    type="button"
                    onClick={() => onOverrideSelection?.(mismatch.visualLeader.sku)}
                    aria-pressed={selectedSku === mismatch.visualLeader.sku}
                    className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                      selectedSku === mismatch.visualLeader.sku
                        ? 'border-accent bg-accent text-white'
                        : 'border-border-strong bg-surface-2 text-foreground hover:border-accent/50'
                    }`}
                  >
                    Show me {mismatch.visualLeader.sku} instead
                  </button>
                </div>
              </>
            ) : (
              <p className="text-sm text-foreground">
                That leaves one match:{' '}
                <span className="font-mono font-semibold">{resolved.sku}</span> -{' '}
                <span className="font-semibold">{resolved.productName}</span>
              </p>
            )}
            <p className="mt-1 text-xs text-muted">
              Selected below. Change any answer above if that doesn&rsquo;t look right.
            </p>
          </ChatBubble>
        )}

        {!resolved && !question && (
          <ChatBubble side="left">
            {(skippedAll || skipped.length > 0) && remaining[0] ? (
              <>
                <p className="text-sm text-foreground">
                  No problem - since you weren&rsquo;t sure, here&rsquo;s our best guess based on your photo:{' '}
                  <span className="font-mono font-semibold">{remaining[0].sku}</span> -{' '}
                  <span className="font-semibold">{remaining[0].productName}</span> (
                  {formatPercent(remaining[0].similarity)} visual match).
                </p>
                <p className="mt-1 text-xs text-muted">
                  It&rsquo;s selected below. Compare it against the other candidates and pick a different one if
                  that&rsquo;s not right.
                </p>
              </>
            ) : (
              <>
                <p className="text-sm text-foreground">
                  {remaining.length} candidates are still possible, and the catalog has nothing further that tells
                  them apart.
                </p>
                <p className="mt-1 text-xs text-muted">
                  Compare the photos below and pick the one that matches your part.
                </p>
              </>
            )}
            {(answers.length > 0 || skippedAll) && (
              <button
                type="button"
                onClick={restart}
                className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-border-strong px-3 py-1.5 text-xs font-semibold text-foreground transition-colors hover:border-accent/50"
              >
                <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                Start over
              </button>
            )}
          </ChatBubble>
        )}
      </div>
    </section>
  )
}
