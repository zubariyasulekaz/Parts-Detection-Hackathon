import { ArrowLeft } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { EmptyState } from '@/components/common/EmptyState'
import { ScanFrame } from '@/components/common/ScanFrame'
import { StatusBadge } from '@/components/common/StatusBadge'
import { PageContainer } from '@/components/layout/PageContainer'
import { AIExplanationPanel } from '@/components/results/AIExplanationPanel'
import { AIMatchSummary } from '@/components/results/AIMatchSummary'
import { CandidateCard } from '@/components/results/CandidateCard'
import { ConfirmationPanel } from '@/components/results/ConfirmationPanel'
import { IdentificationSummary } from '@/components/results/IdentificationSummary'
import { useIdentification } from '@/context/IdentificationContext'
import { HIGH_CONFIDENCE_THRESHOLD } from '@/services/identificationService'
import { formatPercent } from '@/utils/format'

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

export function ResultsPage() {
  const navigate = useNavigate()
  const { result, uploadedImageUrl, selectedSku, selectCandidate, reset } = useIdentification()

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

  const awaitingConfirmation = result.requiresConfirmation && !selectedSku
  const selectedCandidate = result.candidates.find((candidate) => candidate.sku === selectedSku) ?? null
  const isHighConfidence = !result.requiresConfirmation && result.category.confidence >= HIGH_CONFIDENCE_THRESHOLD

  function handleNewSearch() {
    reset()
    navigate('/')
  }

  function goToProduct(sku: string) {
    navigate(`/product/${encodeURIComponent(sku)}`)
  }

  return (
    <PageContainer className="py-12">
      <div className="mb-6 flex items-center justify-between">
        <button
          type="button"
          onClick={handleNewSearch}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-muted transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          New Search
        </button>
        <StatusBadge variant="success">Analysis Complete</StatusBadge>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,380px)_1fr]">
        <div className="shadow-card flex flex-col gap-3 rounded-xl border border-border bg-surface p-6">
          <h2 className="text-sm font-bold tracking-wide text-muted uppercase">Uploaded Part Image</h2>
          <div className="relative aspect-square overflow-hidden rounded-lg border border-border-strong bg-surface-2">
            <img src={uploadedImageUrl} alt="Uploaded part" className="h-full w-full object-contain p-4" />
            <ScanFrame
              label={
                awaitingConfirmation
                  ? undefined
                  : `${result.category.name.toUpperCase()} · ${formatPercent(result.category.confidence)}`
              }
              labelTone={isHighConfidence ? 'success' : awaitingConfirmation ? 'warning' : 'accent'}
            />
          </div>
          <p className="text-xs text-muted">
            Image quality: <span className="font-semibold text-foreground">{capitalize(result.imageQuality)}</span>
          </p>
        </div>

        <IdentificationSummary
          category={result.category}
          selectedCandidate={selectedCandidate}
          isHighConfidence={isHighConfidence}
          onViewProduct={() => selectedCandidate && goToProduct(selectedCandidate.sku)}
          onConfirmMatch={() => selectedCandidate && goToProduct(selectedCandidate.sku)}
        />
      </div>

      {awaitingConfirmation && (
        <div className="mt-6 animate-fade-slide-up">
          <ConfirmationPanel reason={result.confirmationReason} />
        </div>
      )}

      <div className="mt-8">
        <h2 className="mb-4 text-sm font-bold tracking-wide text-muted uppercase">Top Candidates</h2>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {result.candidates.map((candidate, index) => (
            <div key={candidate.sku} className="animate-pop-in" style={{ animationDelay: `${index * 90}ms` }}>
              <CandidateCard
                candidate={candidate}
                isSelected={candidate.sku === selectedSku}
                isPrimaryAction={awaitingConfirmation}
                onSelect={() => selectCandidate(candidate.sku)}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="mt-8 grid max-w-4xl gap-5 lg:grid-cols-2">
        <AIMatchSummary result={result} />
        {result.aiExplanation && <AIExplanationPanel explanation={result.aiExplanation} />}
      </div>
    </PageContainer>
  )
}
