import { ArrowLeft } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
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
import { ConfirmationPanel } from '@/components/results/ConfirmationPanel'
import { GuidedDisambiguation } from '@/components/results/GuidedDisambiguation'
import { IdentificationSummary } from '@/components/results/IdentificationSummary'
import { NoCatalogMatchPanel } from '@/components/results/NoCatalogMatchPanel'
import { useIdentification } from '@/context/IdentificationContext'
import { canDisambiguate, type DisambiguationAnswer } from '@/services/disambiguation'
import { HIGH_CONFIDENCE_THRESHOLD, reportConfirmation } from '@/services/identificationService'
import { formatPercent, formatSearchTime } from '@/utils/format'

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

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
  // final pick was reached.
  const answersRef = useRef<DisambiguationAnswer[]>([])
  const headingRef = useRef<HTMLHeadingElement>(null)

  // Announce arrival: without moving focus, a screen-reader user is still
  // sitting on the previous page's button after navigate('/results').
  useEffect(() => {
    headingRef.current?.focus()
  }, [])

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
  // Nothing in the catalog scored high enough to be a match — the page becomes a
  // "we don't stock this" answer rather than a ranked recommendation. The
  // verdict is the server's (mock mode derives it locally).
  const noCatalogMatch = result.noMatch
  const awaitingConfirmation = result.requiresConfirmation && !selectedSku
  const selectedCandidate = candidates.find((candidate) => candidate.sku === selectedSku) ?? null
  const isHighConfidence =
    !noCatalogMatch && !result.requiresConfirmation && result.category.confidence >= HIGH_CONFIDENCE_THRESHOLD
  // What the upload gets compared against: whatever the user picked, else the
  // top-ranked candidate. Nothing to compare when nothing matched closely enough.
  const comparisonCandidate = noCatalogMatch ? null : (selectedCandidate ?? candidates[0] ?? null)

  function handleNewSearch() {
    reset()
    navigate('/')
  }

  function goToProduct(sku: string) {
    navigate(`/product/${encodeURIComponent(sku)}`)
  }

  /** Confirm = record the user's final answer on the audit trail, then show the product. */
  function confirmAndView(sku: string) {
    reportConfirmation(auditId, sku, answersToRecord(answersRef.current))
    goToProduct(sku)
  }

  /** The guided questions ended on exactly one SKU — that outcome is worth recording on its own. */
  function handleResolved(sku: string, answers: DisambiguationAnswer[]) {
    selectCandidate(sku)
    reportConfirmation(auditId, sku, answersToRecord(answers))
  }

  function handleRemainingChange(skus: string[]) {
    setRemainingSkus(skus)
    // An answer can rule out a card the user had already picked by hand. The
    // answer is the newer and more specific statement, so it wins — otherwise
    // the summary would go on showing a SKU the grid has greyed out.
    if (selectedSku && !skus.includes(selectedSku)) {
      const fallback = candidates.find((candidate) => skus.includes(candidate.sku))
      if (fallback) selectCandidate(fallback.sku)
    }
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
              {/* On no-match the guard silences the category chip too — the
                  system refused the match, so it must not caption the photo
                  with a category it couldn't stand behind. */}
              <ScanFrame
                label={
                  noCatalogMatch
                    ? 'NOT RECOGNIZED'
                    : awaitingConfirmation
                      ? undefined
                      : `${result.category.name.toUpperCase()} · ${formatPercent(result.category.confidence)}`
                }
                labelTone={
                  isHighConfidence ? 'success' : awaitingConfirmation || noCatalogMatch ? 'warning' : 'accent'
                }
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
            category={result.category}
            selectedCandidate={selectedCandidate}
            isHighConfidence={isHighConfidence}
            onViewProduct={() => selectedCandidate && goToProduct(selectedCandidate.sku)}
            onConfirmMatch={() => selectedCandidate && confirmAndView(selectedCandidate.sku)}
          />
        )}
      </div>

      {/* Stays mounted once resolved — gating on `awaitingConfirmation` would
          unmount the panel the instant its last answer set the selection,
          taking the answer trail and the "change this" buttons with it. */}
      {result.requiresConfirmation && (
        <div className="mt-6 animate-fade-slide-up">
          {/* Questions where the catalog can answer them; the plain "compare
              these yourself" panel only when nothing distinguishes the tie. */}
          {canDisambiguate(candidates) ? (
            <GuidedDisambiguation
              candidates={candidates}
              onRemainingChange={handleRemainingChange}
              onResolved={handleResolved}
              onAnswersChange={(answers) => {
                answersRef.current = answers
              }}
            />
          ) : (
            <ConfirmationPanel reason={result.confirmationReason} />
          )}
        </div>
      )}

      <div className="mt-8">
        <h2 className="heading-eyebrow text-sm font-bold tracking-wide text-muted uppercase">
          {noCatalogMatch ? 'Closest Catalog Entries' : 'Top Candidates'}
        </h2>
        {noCatalogMatch && (
          <p className="mt-1 text-xs text-muted">
            Shown for reference only — none of these scored high enough to be treated as a match.
          </p>
        )}
        <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {candidates.map((candidate, index) => {
            // Ruled-out candidates stay on screen, dimmed, rather than
            // disappearing — seeing what an answer eliminated is what makes the
            // questions feel like narrowing rather than a black box.
            const ruledOut = remainingSkus !== null && !remainingSkus.includes(candidate.sku)
            return (
              <div
                key={candidate.sku}
                className={`animate-pop-in transition-opacity ${ruledOut ? 'opacity-40 grayscale' : ''}`}
                style={{ animationDelay: `${index * 90}ms` }}
              >
                <CandidateCard
                  candidate={candidate}
                  isSelected={candidate.sku === selectedSku}
                  isPrimaryAction={awaitingConfirmation && !ruledOut}
                  showBestMatch={!noCatalogMatch}
                  isRuledOut={ruledOut}
                  onSelect={() => selectCandidate(candidate.sku)}
                />
              </div>
            )
          })}
        </div>
      </div>

      <div className="mt-8 grid max-w-4xl gap-5 lg:grid-cols-2">
        <AIMatchSummary result={result} />
        {result.aiExplanation && <AIExplanationPanel explanation={result.aiExplanation} />}
      </div>
    </PageContainer>
  )
}
