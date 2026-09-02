import { Check, CircleSlash, Loader2, X } from 'lucide-react'
import { ConfidenceGauge } from '@/components/common/ConfidenceGauge'
import { ProductThumbnail } from '@/components/common/ProductThumbnail'
import { ScanFrame } from '@/components/common/ScanFrame'
import { formatPercent } from '@/utils/format'
import type { BatchVerdict } from '@/services/batchTest'
import type { IdentificationResult } from '@/types/identification'

export interface BatchRowState {
  id: string
  fileName: string
  /** Object URL for the uploaded photograph. Revoked when the page unmounts. */
  previewUrl: string
  status: 'waiting' | 'running' | 'done' | 'failed'
  expectedSku: string | null
  verdict: BatchVerdict
  result: IdentificationResult | null
  error: string | null
}

const VERDICT_STYLE: Record<BatchVerdict, { label: string; className: string }> = {
  top1: { label: 'Exact match', className: 'border-success/40 bg-success/10 text-success-soft' },
  top5: { label: 'In the top five', className: 'border-accent/40 bg-accent/10 text-accent-soft' },
  miss: { label: 'Not found', className: 'border-warning/40 bg-warning/10 text-warning-soft' },
  unscored: { label: 'No SKU in filename', className: 'border-border-strong bg-surface-2 text-subtle' },
}

function VerdictIcon({ verdict }: { verdict: BatchVerdict }) {
  if (verdict === 'top1') return <Check className="h-3.5 w-3.5" aria-hidden="true" />
  if (verdict === 'miss') return <X className="h-3.5 w-3.5" aria-hidden="true" />
  if (verdict === 'unscored') return <CircleSlash className="h-3.5 w-3.5" aria-hidden="true" />
  return null
}

interface BatchMatchRowProps {
  row: BatchRowState
  index: number
  /** This row's full result is being re-run before the results page opens. */
  opening?: boolean
  onOpen: (row: BatchRowState) => void
}

/**
 * One photograph's result: the upload, the score, and what the catalogue
 * returned - the same three things the results page leads with, sized so
 * fifteen of them can be read in one scroll.
 *
 * The verdict chip is the reason this view exists. A 45% match tells a viewer
 * nothing on its own; "45%, and it was the right part" and "45%, and it was
 * not" are opposite outcomes, and only the filename knows which.
 */
export function BatchMatchRow({ row, index, opening = false, onOpen }: BatchMatchRowProps) {
  const top = row.result?.candidates[0] ?? null
  const noMatch = row.result?.noMatch ?? false
  const verdictStyle = VERDICT_STYLE[row.verdict]

  return (
    <section className="shadow-card rounded-xl border border-border bg-surface p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="shrink-0 rounded-md border border-border-strong bg-surface-2 px-2 py-0.5 font-mono text-xs text-subtle">
            {String(index + 1).padStart(2, '0')}
          </span>
          <h3 className="truncate font-mono text-sm font-semibold text-foreground" title={row.fileName}>
            {row.fileName}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {row.expectedSku && (
            <span className="rounded-md border border-border-strong bg-surface-2 px-2 py-0.5 font-mono text-xs text-muted">
              expected {row.expectedSku}
            </span>
          )}
          {row.status === 'done' && (
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${verdictStyle.className}`}
            >
              <VerdictIcon verdict={row.verdict} />
              {verdictStyle.label}
            </span>
          )}
        </div>
      </div>

      {row.status === 'waiting' && (
        <p className="py-10 text-center text-xs text-subtle">Queued</p>
      )}

      {row.status === 'running' && (
        <p className="flex items-center justify-center gap-2 py-10 text-xs text-muted">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Searching the catalogue…
        </p>
      )}

      {row.status === 'failed' && (
        <p className="py-10 text-center text-xs text-warning-soft">{row.error ?? 'This photo could not be searched.'}</p>
      )}

      {row.status === 'done' && row.result && (
        <>
          <div className="grid items-center gap-4 sm:grid-cols-[1fr_auto_1fr]">
            <figure className="mx-auto flex w-full max-w-xs flex-col gap-2">
              <div className="relative aspect-square min-h-0 overflow-hidden rounded-xl border border-border-strong bg-surface-2">
                <img src={row.previewUrl} alt={row.fileName} className="h-full w-full object-contain p-4" />
                <ScanFrame
                  label={
                    noMatch
                      ? 'NOT RECOGNIZED'
                      : `${row.result.category.name.toUpperCase()} · ${formatPercent(row.result.category.confidence)}`
                  }
                  labelTone={noMatch ? 'warning' : 'accent'}
                />
              </div>
              <figcaption className="text-center text-xs font-semibold tracking-wide text-subtle uppercase">
                Your photo
              </figcaption>
            </figure>

            {top && (
              <div className="flex flex-row items-center justify-center gap-3 sm:flex-col sm:gap-2">
                <ConfidenceGauge
                  value={top.similarity}
                  size={88}
                  tone={noMatch ? 'warning' : 'accent'}
                  label="Visual similarity between this photo and the catalogue match"
                />
                <p className="text-xs font-semibold tracking-wide text-subtle uppercase sm:text-center">
                  Visual
                  <br className="hidden sm:inline" /> match
                </p>
              </div>
            )}

            {top && (
              <figure className="mx-auto flex w-full max-w-xs flex-col gap-2">
                <div className="relative aspect-square overflow-hidden rounded-xl border border-border-strong bg-surface-2 p-4">
                  <ProductThumbnail
                    category={top.category}
                    images={top.imageUrl ? [top.imageUrl] : []}
                    className="h-full w-full"
                  />
                  <span className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-md border border-border-strong bg-surface/90 px-2.5 py-1 font-mono text-xs font-semibold whitespace-nowrap text-muted backdrop-blur">
                    {top.sku}
                  </span>
                </div>
                <figcaption className="line-clamp-2 text-center text-xs font-semibold tracking-wide text-subtle uppercase">
                  {top.brand} · {top.productName}
                </figcaption>
              </figure>
            )}
          </div>

          {/* The runners-up, as scores only. Where the expected SKU sits at
              rank 3, this is what shows it - and the gap between first and
              second is the system's own confidence, which is worth seeing
              beside a verdict. */}
          <div className="mt-4 flex flex-wrap items-center justify-center gap-1.5 border-t border-border pt-3.5">
            {row.result.candidates.map((candidate) => {
              const isExpected = candidate.sku === row.expectedSku
              return (
                <span
                  key={candidate.sku}
                  className={`rounded-md border px-2 py-0.5 font-mono text-xs ${
                    isExpected
                      ? 'border-success/40 bg-success/10 text-success-soft'
                      : 'border-border-strong bg-surface-2 text-subtle'
                  }`}
                >
                  {candidate.rank}. {candidate.sku} · {formatPercent(candidate.similarity)}
                </span>
              )
            })}
            <button
              type="button"
              disabled={opening}
              onClick={() => onOpen(row)}
              className="inline-flex items-center gap-1.5 rounded-md border border-border-strong px-2.5 py-0.5 text-xs font-semibold text-muted transition-colors hover:border-accent/50 hover:text-foreground disabled:opacity-60"
            >
              {opening && <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />}
              {opening ? 'Opening…' : 'View info'}
            </button>
          </div>
        </>
      )}
    </section>
  )
}
