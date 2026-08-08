import { Sparkles } from 'lucide-react'

interface AIExplanationPanelProps {
  explanation: string
}

/**
 * Brain 4's (Qwen LLM) free-form output, rendered verbatim - never parsed
 * or restructured into fabricated UI (e.g. fake "question" chips). Styled
 * distinctly from AIMatchSummary so it reads as generated commentary, not
 * a computed fact from the similarity/confidence scores.
 */
export function AIExplanationPanel({ explanation }: AIExplanationPanelProps) {
  return (
    <div className="shadow-card rounded-xl border border-accent/20 bg-surface p-5">
      <div className="flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent/15 text-accent-soft">
          <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
        </span>
        <h2 className="text-sm font-bold text-foreground">AI Explanation</h2>
        <span className="ml-auto rounded-full border border-border-strong bg-surface-2 px-2 py-0.5 font-mono text-xs font-semibold tracking-wide text-subtle uppercase">
          Brain 4 · Qwen
        </span>
      </div>
      <p className="mt-3 border-l-2 border-accent/30 pl-3 text-sm leading-relaxed whitespace-pre-line text-foreground/90">
        {explanation}
      </p>
    </div>
  )
}
