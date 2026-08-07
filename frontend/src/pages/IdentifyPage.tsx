import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { ScanFrame } from '@/components/common/ScanFrame'
import { Tilt3D } from '@/components/common/Tilt3D'
import { AmbientBackground } from '@/components/layout/AmbientBackground'
import { PageContainer } from '@/components/layout/PageContainer'
import { ProcessingPipeline } from '@/components/processing/ProcessingPipeline'
import { useIdentification } from '@/context/IdentificationContext'
import { PROCESSING_STAGE_DEFINITIONS } from '@/services/identificationService'

const STAGE_COUNT = PROCESSING_STAGE_DEFINITIONS.length

export function IdentifyPage() {
  const navigate = useNavigate()
  const { status, pendingFile, uploadedImageUrl, currentStage, error, runIdentification, reset } = useIdentification()
  const hasStarted = useRef(false)
  // The bar creeps toward the next stage milestone while a stage is in
  // flight. The real pipeline spends most of its time inside one blocking
  // request; a bar that freezes at 33% for that whole stretch reads as a
  // hang even when everything is fine.
  const [displayPercent, setDisplayPercent] = useState(0)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  useEffect(() => {
    if (!pendingFile || hasStarted.current) return
    hasStarted.current = true
    runIdentification()
      .then(() => navigate('/results'))
      .catch(() => {
        /* handled via status === 'error' below */
      })
  }, [pendingFile, runIdentification, navigate])

  function handleRetry() {
    hasStarted.current = false
    runIdentification()
      .then(() => navigate('/results'))
      .catch(() => {
        hasStarted.current = false
      })
  }

  const isProcessing = status === 'processing'
  const isDone = status === 'success' || status === 'ambiguous'
  const stageIndex = currentStage ? PROCESSING_STAGE_DEFINITIONS.findIndex((definition) => definition.key === currentStage) : -1

  // Wall-clock counter: honest feedback for a cold backend still loading models.
  useEffect(() => {
    if (!isProcessing) return
    const startedAt = Date.now()
    setElapsedSeconds(0)
    const timer = setInterval(() => setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000)), 500)
    return () => clearInterval(timer)
  }, [isProcessing])

  // Ease toward just short of the next milestone; jump on real stage events.
  useEffect(() => {
    if (isDone) {
      setDisplayPercent(100)
      return
    }
    if (!isProcessing) return
    const floor = ((stageIndex + 1) / STAGE_COUNT) * 100
    const ceiling = ((stageIndex + 2) / STAGE_COUNT) * 100 - 3
    const timer = setInterval(() => {
      setDisplayPercent((current) => {
        const base = Math.max(current, floor)
        return base + (Math.min(ceiling, 97) - base) * 0.03
      })
    }, 100)
    return () => clearInterval(timer)
  }, [stageIndex, isProcessing, isDone])

  function handleStartOver() {
    reset()
    navigate('/')
  }

  if (!pendingFile) {
    return (
      <PageContainer className="py-20">
        <EmptyState
          title="No image is queued for identification"
          description="Start from the landing page to upload a part photo or try the sample image."
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

  const activeDefinition = PROCESSING_STAGE_DEFINITIONS[Math.min(stageIndex + 1, STAGE_COUNT - 1)]
  const stageNumber = Math.min(stageIndex + 2, STAGE_COUNT)
  // Short by construction. The frame chip is ~150px wide and ellipsises, so a
  // full stage name rendered here as "RETRIEVING PR…" - unreadable, and the
  // long form already has a proper home in the stage panel beside it.
  const frameLabel = isDone ? 'MATCH LOCKED' : isProcessing ? `STAGE ${stageNumber}/${STAGE_COUNT}` : undefined
  const progressPercent = Math.round(displayPercent)

  return (
    <div className="relative overflow-hidden">
      <AmbientBackground className="opacity-70" />
      <PageContainer className="relative py-8 lg:py-12">
        <div className="mx-auto max-w-5xl">
          <p className="heading-eyebrow text-xs font-bold tracking-[0.2em] text-accent-soft uppercase">
            {isDone ? 'Analysis complete' : 'Analyzing'}
          </p>
          <h1 className="mt-3 text-2xl font-bold text-foreground sm:text-3xl">
            Reading your <span className="text-gradient-accent">part</span>.
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
            Running the image through PartPilot&apos;s classification and similarity-search pipeline.
          </p>

          {status === 'error' ? (
            <div className="mt-8 flex max-w-xl flex-col items-start gap-4">
              <ErrorState message={error ?? 'Identification failed. Please try again.'} onRetry={handleRetry} />
              <button
                type="button"
                onClick={handleStartOver}
                className="text-sm font-medium text-muted underline-offset-4 hover:text-foreground hover:underline"
              >
                Start over with a new image
              </button>
            </div>
          ) : (
            // Two columns instead of one narrow stack: the image was 160px in a
            // centred column, too small to actually inspect while the thing the
            // page is about is "look at what we're looking at".
            <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,20rem)_1fr] lg:items-start lg:gap-8">
              <div className="flex flex-col gap-4">
                <Tilt3D
                  intensity="subtle"
                  glare
                  className="shadow-depth aspect-square overflow-hidden rounded-2xl border border-accent/20 bg-surface p-5"
                >
                  {uploadedImageUrl && (
                    <img src={uploadedImageUrl} alt="Uploaded part" className="h-full w-full object-contain" />
                  )}
                  <ScanFrame active={isProcessing} label={frameLabel} labelTone={isDone ? 'success' : 'accent'} />
                </Tilt3D>

                <div>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="font-mono text-2xl leading-none font-bold text-foreground">
                      {progressPercent}
                      <span className="text-base text-subtle">%</span>
                    </span>
                    {isProcessing && elapsedSeconds >= 3 && (
                      <span className="font-mono text-xs text-subtle">{elapsedSeconds}s elapsed</span>
                    )}
                  </div>
                  <div className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
                    <div
                      className="shadow-glow-accent h-full rounded-full bg-linear-to-r from-accent to-accent-2 transition-all duration-300 ease-out"
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                </div>
              </div>

              <div className="shadow-depth animate-fade-in rounded-2xl border border-border bg-surface p-6">
                {/* The full stage name lives here, where there is room for it. */}
                <div className="mb-5 flex items-start justify-between gap-4 border-b border-border pb-4">
                  <div className="min-w-0">
                    <p className="text-xs font-bold tracking-[0.2em] text-subtle uppercase">Current stage</p>
                    <p className="mt-1.5 text-base font-semibold text-foreground">
                      {isDone ? 'Match locked' : activeDefinition.activeLabel}
                    </p>
                  </div>
                  <span className="shrink-0 rounded-full border border-border-strong bg-surface-2 px-2.5 py-1 font-mono text-xs font-semibold text-muted">
                    {isDone ? STAGE_COUNT : stageNumber}/{STAGE_COUNT}
                  </span>
                </div>

                <ProcessingPipeline
                  currentStage={currentStage}
                  isComplete={status === 'success' || status === 'ambiguous'}
                />

                {isProcessing && elapsedSeconds >= 15 && (
                  <p className="animate-fade-in mt-5 border-t border-border pt-4 text-xs leading-relaxed text-muted">
                    First run after a backend restart loads the models - this can take up to a minute.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </PageContainer>
    </div>
  )
}
