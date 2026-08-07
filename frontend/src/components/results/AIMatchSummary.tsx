import { CircleCheck, TriangleAlert } from 'lucide-react'
import { NO_CATALOG_MATCH_THRESHOLD, STRONG_SEPARATION_GAP } from '@/services/identificationService'
import { formatPercent } from '@/utils/format'
import type { IdentificationResult } from '@/types/identification'

interface SummaryLine {
  tone: 'positive' | 'caution'
  text: string
}

/**
 * Every line here is derived only from data the pipeline actually returns -
 * predicted category, similarity scores, and rank - never from claims about
 * physical features the model doesn't inspect.
 */
function buildSummaryLines(result: IdentificationResult): SummaryLine[] {
  const [top, runnerUp] = result.candidates

  // On a no-match verdict the guard silences Brain 1 too: an image nothing
  // matched gets no category claim, because "Suspension Bushing · 55%" over
  // a photo of a living room is a statement the system cannot stand behind.
  if (result.noMatch) {
    const threshold = result.noMatchThreshold ?? NO_CATALOG_MATCH_THRESHOLD
    const lines: SummaryLine[] = [
      { tone: 'caution', text: 'The image was not recognized as a catalog part' },
      {
        tone: 'caution',
        text: top
          ? `No catalog entry cleared the ${formatPercent(threshold)} match threshold; the closest scored ${formatPercent(top.similarity)}`
          : 'The visual search returned no catalog entries for this part',
      },
    ]
    return lines
  }

  const lines: SummaryLine[] = [{ tone: 'positive', text: `Predicted category: ${result.category.name}` }]

  if (top) {
    lines.push({
      tone: 'positive',
      text: `Highest visual similarity among catalog candidates (${formatPercent(top.similarity)})`,
    })
  }

  if (top && runnerUp) {
    const gap = top.similarity - runnerUp.similarity
    if (gap >= STRONG_SEPARATION_GAP) {
      lines.push({
        tone: 'positive',
        text: `Strong score separation from lower-ranked candidates (+${formatPercent(gap)})`,
      })
    } else {
      lines.push({
        tone: 'caution',
        text: `Close score separation from the next candidate (${formatPercent(gap)} apart), so confirmation is recommended`,
      })
    }
  }

  return lines
}

interface AIMatchSummaryProps {
  result: IdentificationResult
}

export function AIMatchSummary({ result }: AIMatchSummaryProps) {
  const lines = buildSummaryLines(result)

  return (
    <div className="shadow-card rounded-xl border border-border bg-surface p-5">
      <h2 className="heading-eyebrow text-sm font-bold text-foreground">AI Match Summary</h2>
      <ul className="mt-3 flex flex-col gap-2.5">
        {lines.map((line) => (
          <li key={line.text} className="flex items-start gap-2 text-sm text-muted">
            {line.tone === 'positive' ? (
              <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-success" aria-hidden="true" />
            ) : (
              <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden="true" />
            )}
            <span>{line.text}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
