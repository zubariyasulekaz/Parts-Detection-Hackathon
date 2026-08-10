import { ArrowLeft } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ConfidenceGauge } from '@/components/common/ConfidenceGauge'
import { EmptyState } from '@/components/common/EmptyState'
import { ProductThumbnail } from '@/components/common/ProductThumbnail'
import { ScanFrame } from '@/components/common/ScanFrame'
import { StatusBadge } from '@/components/common/StatusBadge'
import { PageContainer } from '@/components/layout/PageContainer'
import { AIExplanationPanel } from '@/components/results/AIExplanationPanel'
import { AIMatchSummary } from '@/components/results/AIMatchSummary'
import { CandidateCard } from '@/components/results/CandidateCard'
import { GuidedDisambiguation } from '@/components/results/GuidedDisambiguation'
import { IdentificationSummary } from '@/components/results/IdentificationSummary'
import { ServerChatPanel } from '@/components/results/ServerChatPanel'
import { NoCatalogMatchPanel } from '@/components/results/NoCatalogMatchPanel'
import { useIdentification } from '@/context/IdentificationContext'
import {
  canDisambiguate,
  detectVisualMismatch,
  isDecisiveVisualMatch,
  type DisambiguationAnswer,
} from '@/services/disambiguation'
import { HIGH_CONFIDENCE_THRESHOLD, reportConfirmation } from '@/services/identificationService'
import { formatPercent, formatSearchTime } from '@/utils/format'

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

/**
 * Whether the guided questions run through the backend chat API instead of
 * the local logic. Server sessions only exist in live mode; mock mode always
 * runs the local flow, which the API mirrors one-for-one.
 */
const USE_SERVER_CHAT =
  import.meta.env.VITE_API_MODE === 'live' &&
  String(import.meta.env.VITE_CHAT_API ?? '').toLowerCase() === 'true'

/** `[{facet: "make", label: "Honda"}]` -> `{make: "Honda"}` for the audit trail. */
function answersToRecord(answers: DisambiguationAnswer[]): Record<string, string> | undefined {
  if (!answers.length) return undefined
  return Object.fromEntries(answers.map((entry) => [entry.facet, entry.label]))
}

export function ResultsPage() {
  const navigate = useNavigate()
  const { result, uploadedImageUrl, selectedSku, selectCandidate, reset } = useIdentification()
  // SKUs the guided questions have not ruled out. Null until the first answer,
  // meaning "everything is still in play".
  const [remainingSkus, setRemainingSkus] = useState<string[] | null>(null)
  // The guided Q&A trail, lifted here so Confirm Match can report how the
  // final pick was reached, and so the match summary can explain itself
  // ("confirmed by 2 answers" / visual-mismatch warning) once revealed.
  const [answers, setAnswers] = useState<DisambiguationAnswer[]>([])
  const headingRef = useRef<HTMLHeadingElement>(null)

  // Whether there is anything worth asking about the top candidates before
  // showing their photos. False (nothing to ask) starts the page already
  // revealed; true holds images back until the guided questions finish.
  //
  // `requiresConfirmation` is the gate that matters: it is set when rank 1 and
  // rank 2 are too close to auto-pick from. Questions are for the case where
  // the photo could not decide - two parts that are the same object shot
  // twice - not for every result. Deliberately not gated on the absolute
  // score: a weak-but-clear winner needs no questions, while a 95% match with
  // a 94% runner-up is exactly when we must ask.
  const needsQuestions = Boolean(
    result &&
      !result.noMatch &&
      result.candidates.length > 1 &&
      result.requiresConfirmation &&
      canDisambiguate(result.candidates),
  )
  // Gates the catalog-match comparison, summary and image grid. Starts
  // revealed only when there is nothing to ask; otherwise the guided
  // questions must finish first (see `handleFinished`).
  const [revealed, setRevealed] = useState(!needsQuestions)
  // Whether the answer trail has ruled out the candidate the photo itself
  // most strongly favored - drives the match summary's caution copy.
  const mismatch = useMemo(
    () => (result ? detectVisualMismatch(result.candidates, answers) : null),
    [result, answers],
  )

  // Announce arrival: without moving focus, a screen-reader user is still
  // sitting on the previous page's button after navigate('/results').
  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  // Once the page has something to show, default to the closest visual match
  // rather than leaving the user with nothing selected - the person who
  // uploaded a photo may not know the product details, so "Not sure"/"Skip
  // questions" (or scores too close to auto-pick from the start) should
  // still land on the system's best guess. This only decides what's shown as
  // the suggestion; "Confirm Match" is still the only thing that finalizes it.
  useEffect(() => {
    if (!result || result.noMatch || selectedSku || !revealed) return
    const pool = remainingSkus ?? result.candidates.map((candidate) => candidate.sku)
    const closest = result.candidates.find((candidate) => pool.includes(candidate.sku))
    if (closest) selectCandidate(closest.sku)
  }, [result, selectedSku, revealed, remainingSkus, selectCandidate])

  if (!result || !uploadedImageUrl) {
    return (
      <PageContainer className="py-20">
        <EmptyState
          title="No identification result yet"
          description="Upload a part photo from the landing page to see catalog matches here."
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
      </PageContainer>
    )
  }

  // Captured after the guard above: the function declarations below are hoisted,
  // so TypeScript cannot carry the non-null narrowing of `result` into them.
  const candidates = result.candidates
  const auditId = result.auditId
  // Nothing in the catalog scored high enough to be a match - the page becomes a
  // "we don't stock this" answer rather than a ranked recommendation. The
  // verdict is the server's (mock mode derives it locally).
  const noCatalogMatch = result.noMatch
  const selectedCandidate = candidates.find((candidate) => candidate.sku === selectedSku) ?? null
  const isHighConfidence =
    !noCatalogMatch && !result.requiresConfirmation && result.category.confidence >= HIGH_CONFIDENCE_THRESHOLD
  // Whether the pick is the photo's own decisive favorite - independent of
  // Brain 1's category confidence, so a 98% visual match doesn't read as
  // "unconfirmed" just because the classifier itself was unsure.
  const isDecisiveMatch = Boolean(selectedCandidate && isDecisiveVisualMatch(candidates, selectedCandidate.sku))
  // Whether the *current* pick is actually what the answer trail narrowed
  // down to - not just "some answers were given". The candidate grid keeps
  // ruled-out cards pickable, so a manual click after answering can select
  // something the answers themselves excluded; "Your Match" shouldn't claim
  // that pick was "confirmed by your answers" when it wasn't.
  const confirmedByAnswers = Boolean(
    answers.length > 0 &&
      remainingSkus !== null &&
      remainingSkus.length === 1 &&
      selectedCandidate?.sku === remainingSkus[0],
  )
  // What the upload gets compared against: whatever the user picked, else the
  // top-ranked candidate. Nothing to compare while the guided questions are
  // still running - that comparison IS the reveal the questions lead up to.
  const comparisonCandidate = !revealed || noCatalogMatch ? null : (selectedCandidate ?? candidates[0] ?? null)

  function handleNewSearch() {
    reset()
    navigate('/')
  }

  function goToProduct(sku: string) {
    navigate(`/product/${encodeURIComponent(sku)}`)
  }

  /** Confirm = record the user's final answer on the audit trail, then show the product. */
  function confirmAndView(sku: string) {
    reportConfirmation(auditId, sku, answersToRecord(answers))
    goToProduct(sku)
  }

  /** The guided questions ended on exactly one SKU - that outcome is worth recording on its own. */
  function handleResolved(sku: string, answers: DisambiguationAnswer[]) {
    selectCandidate(sku)
    reportConfirmation(auditId, sku, answersToRecord(answers))
  }

  function handleRemainingChange(skus: string[]) {
    setRemainingSkus(skus)
    // An answer can rule out a card the user had already picked by hand. The
    // answer is the newer and more specific statement, so it wins - otherwise
    // the summary would go on showing a SKU the grid has greyed out.
    if (selectedSku && !skus.includes(selectedSku)) {
      const fallback = candidates.find((candidate) => skus.includes(candidate.sku))
      if (fallback) selectCandidate(fallback.sku)
    }
  }

  /** Nothing left to ask - resolved, exhausted, or skipped. Time to reveal images. */
  function handleFinished(skus: string[]) {
    setRemainingSkus(skus)
    setRevealed(true)
  }

  return (
    <PageContainer className="py-12">
      <h1 ref={headingRef} tabIndex={-1} className="sr-only">
        Identification results
      </h1>
      <div className="mb-6 flex items-center justify-between">
        <button
          type="button"
          onClick={handleNewSearch}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-muted transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          New Search
        </button>
        <StatusBadge variant={noCatalogMatch ? 'warning' : 'success'}>
          {noCatalogMatch ? 'No Catalog Match' : 'Analysis Complete'}
        </StatusBadge>
      </div>

      {/* The comparison is the hero: "is this actually my part?" is the question
          the whole page exists to answer, and only these two photos answer it.
          Everything else is supporting detail and sits below. */}
      <section className="shadow-card rounded-xl border border-border bg-surface p-6 sm:p-8">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-2">
          <h2 className="heading-eyebrow text-sm font-bold tracking-wide text-muted uppercase">
            {comparisonCandidate ? 'Uploaded vs. Catalog Match' : 'Uploaded Part Image'}
          </h2>
          <p className="text-xs text-muted">
            {result.searchTimeMs > 0 && (
              <>
                Matched in{' '}
                <span className="font-mono font-semibold text-foreground">
                  {formatSearchTime(result.searchTimeMs)}
                </span>
                <span aria-hidden="true"> · </span>
              </>
            )}
            Image quality: <span className="font-semibold text-foreground">{capitalize(result.imageQuality)}</span>
          </p>
        </div>

        <div
          className={
            comparisonCandidate
              ? 'grid items-center gap-5 sm:grid-cols-[1fr_auto_1fr]'
              : 'mx-auto w-full max-w-md'
          }
        >
          <figure className="mx-auto flex w-full max-w-sm flex-col gap-2">
            {/* min-h-0: as a flex item this box's automatic minimum height is
                its content's, which a portrait upload would push past the
                square ratio. */}
            <div className="relative aspect-square min-h-0 overflow-hidden rounded-xl border border-border-strong bg-surface-2">
              <img src={uploadedImageUrl} alt="Uploaded part" className="h-full w-full object-contain p-5" />
              {/* On no-match the guard silences the category chip too - the
                  system refused the match, so it must not caption the photo
                  with a category it couldn't stand behind. */}
              <ScanFrame
                label={
                  noCatalogMatch
                    ? 'NOT RECOGNIZED'
                    : `${result.category.name.toUpperCase()} · ${formatPercent(result.category.confidence)}`
                }
                labelTone={isHighConfidence ? 'success' : noCatalogMatch ? 'warning' : 'accent'}
              />
            </div>
            <figcaption className="text-center text-xs font-semibold tracking-wide text-subtle uppercase">
              Your photo
            </figcaption>
          </figure>

          {comparisonCandidate && (
            <div className="flex flex-row items-center justify-center gap-3 sm:flex-col sm:gap-2">
              <ConfidenceGauge
                value={comparisonCandidate.similarity}
                size={104}
                tone={isHighConfidence ? 'success' : noCatalogMatch ? 'warning' : 'accent'}
                label="Visual similarity between your photo and the catalog match"
              />
              <p className="text-xs font-semibold tracking-wide text-subtle uppercase sm:text-center">
                Visual
                <br className="hidden sm:inline" /> match
              </p>
            </div>
          )}

          {comparisonCandidate && (
            <figure className="mx-auto flex w-full max-w-sm flex-col gap-2">
              {/* Padding sits on the frame, not the thumbnail: the photo is
                  absolutely positioned inside it and would ignore it there. */}
              <div className="relative aspect-square overflow-hidden rounded-xl border border-border-strong bg-surface-2 p-5">
                <ProductThumbnail
                  category={comparisonCandidate.category}
                  images={comparisonCandidate.imageUrl ? [comparisonCandidate.imageUrl] : []}
                  className="h-full w-full"
                />
                <span className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-md border border-border-strong bg-surface/90 px-2.5 py-1 font-mono text-xs font-semibold whitespace-nowrap text-muted backdrop-blur">
                  {comparisonCandidate.sku}
                </span>
              </div>
              <figcaption className="text-center text-xs font-semibold tracking-wide text-subtle uppercase">
                {comparisonCandidate.brand} · {comparisonCandidate.productName}
              </figcaption>
            </figure>
          )}
        </div>
      </section>

      {/* Runs before any product image is shown, not just as a tie-breaker -
          the catalog's own attributes (and, failing that, the full product
          descriptions) can tell the top candidates apart, so ask rather than
          make the user guess from photos of look-alike parts. Sits above the
          match summary below: this is where a mismatch actually gets
          resolved (the "Yes, use X" / "Show me Y instead" choice), so the
          summary can point up to it instead of re-explaining the same
          conflict. Stays mounted once finished so the answer trail and
          "change this" buttons survive into the revealed page below. */}
      {needsQuestions && (
        <div className="mt-6 animate-fade-slide-up">
          {USE_SERVER_CHAT ? (
            <ServerChatPanel
              candidates={candidates}
              onRemainingChange={handleRemainingChange}
              onResolved={handleResolved}
              onAnswersChange={setAnswers}
              onFinished={handleFinished}
              onOverrideSelection={selectCandidate}
              selectedSku={selectedSku}
            />
          ) : (
            <GuidedDisambiguation
              candidates={candidates}
              onRemainingChange={handleRemainingChange}
              onResolved={handleResolved}
              onAnswersChange={setAnswers}
              onFinished={handleFinished}
              onOverrideSelection={selectCandidate}
              selectedSku={selectedSku}
            />
          )}
        </div>
      )}

      {/* Held back until the guided questions above finish - a summary of
          "the" match is exactly what those questions exist to avoid
          presupposing. No-match skips the questions entirely, so its panel
          is never gated. */}
      {(noCatalogMatch || revealed) && (
        <div className="mt-6">
          {noCatalogMatch ? (
            <NoCatalogMatchPanel
              category={result.category}
              closestCandidate={candidates[0] ?? null}
              threshold={result.noMatchThreshold}
              onNewSearch={handleNewSearch}
            />
          ) : (
            <IdentificationSummary
              selectedCandidate={selectedCandidate}
              isHighConfidence={isHighConfidence}
              isDecisiveMatch={isDecisiveMatch}
              answeredQuestions={answers.length}
              confirmedByAnswers={confirmedByAnswers}
              mismatch={mismatch}
              onConfirmMatch={() => selectedCandidate && confirmAndView(selectedCandidate.sku)}
            />
          )}
        </div>
      )}

      {/* Held back until the questions above finish, and empty on a no-match -
          there is no candidate list at all. Every original candidate stays
          visible even after the guided questions narrow things down: the
          answers are the user's own input, not an infallible filter, so a
          card they ruled out (accidentally, or because they changed their
          mind) is marked "Ruled out" rather than removed - still there,
          still pickable, just not the assumed choice. */}
      {!noCatalogMatch && revealed && (
        <div className="mt-8">
          <h2 className="heading-eyebrow text-sm font-bold tracking-wide text-muted uppercase">Top Candidates</h2>
          <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {candidates.map((candidate, index) => (
              <div key={candidate.sku} className="animate-pop-in" style={{ animationDelay: `${index * 90}ms` }}>
                <CandidateCard
                  candidate={candidate}
                  isSelected={candidate.sku === selectedSku}
                  isPrimaryAction={!selectedSku}
                  isRuledOut={remainingSkus !== null && !remainingSkus.includes(candidate.sku)}
                  onSelect={() => selectCandidate(candidate.sku)}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Brain 4's explanation names the top match by design, so it waits for
          the same reveal as the rest of the answer. */}
      {(noCatalogMatch || revealed) && (
        <div className="mt-8 grid max-w-4xl gap-5 lg:grid-cols-2">
          <AIMatchSummary result={result} />
          {result.aiExplanation && <AIExplanationPanel explanation={result.aiExplanation} />}
        </div>
      )}
    </PageContainer>
  )
}
