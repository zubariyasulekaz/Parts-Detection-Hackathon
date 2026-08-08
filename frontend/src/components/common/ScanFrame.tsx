interface ScanFrameProps {
  /** Shows the moving scan sweep and brighter, pulsing corners - the "actively analyzing" state. */
  active?: boolean
  /** Optional floating readout chip, e.g. "SHOCK ABSORBERS · 94%". */
  label?: string
  labelTone?: 'accent' | 'success' | 'warning'
  className?: string
}

const CORNER_BASE = 'animate-scan-lock absolute h-6 w-6 transition-colors duration-300'

const LABEL_TONE_CLASS: Record<NonNullable<ScanFrameProps['labelTone']>, string> = {
  accent: 'border-accent/40 bg-accent-muted/85 text-accent-soft',
  success: 'border-success/40 bg-success-muted/85 text-success-soft',
  warning: 'border-warning/40 bg-warning-muted/85 text-warning-soft',
}

/**
 * A computer-vision "detection frame" - corner brackets, an optional
 * scanning sweep, and an optional locked-on label chip. This is PartPilot's
 * recurring signature motif: it appears over the uploaded image at every
 * stage (upload preview, processing, results) so the whole journey reads
 * as one continuous visual-inspection process rather than disconnected
 * screens.
 */
export function ScanFrame({ active = false, label, labelTone = 'accent', className = '' }: ScanFrameProps) {
  const cornerColor = active ? 'border-accent-soft' : 'border-accent/40'

  return (
    <div aria-hidden="true" className={`pointer-events-none absolute inset-0 ${className}`}>
      <span
        style={{ animationDelay: '0ms' }}
        className={`${CORNER_BASE} ${cornerColor} top-3 left-3 rounded-tl-md border-t-2 border-l-2`}
      />
      <span
        style={{ animationDelay: '60ms' }}
        className={`${CORNER_BASE} ${cornerColor} top-3 right-3 rounded-tr-md border-t-2 border-r-2`}
      />
      <span
        style={{ animationDelay: '60ms' }}
        className={`${CORNER_BASE} ${cornerColor} bottom-3 left-3 rounded-bl-md border-b-2 border-l-2`}
      />
      <span
        style={{ animationDelay: '120ms' }}
        className={`${CORNER_BASE} ${cornerColor} bottom-3 right-3 rounded-br-md border-b-2 border-r-2`}
      />

      {active && (
        <div className="animate-scan-line absolute inset-x-[10%] top-1/2 h-0.5 bg-linear-to-r from-transparent via-accent-soft to-transparent shadow-[0_0_16px_2px_rgba(47,128,237,0.6)]" />
      )}

      {label && (
        <span
          style={{ animationDelay: '260ms' }}
          // whitespace-nowrap: a long readout like "SHOCK ABSORBER · 40%" was
          // wrapping to three lines in a narrow frame and covering the part.
          className={`animate-pop-in absolute bottom-3 left-1/2 max-w-[calc(100%-1.5rem)] -translate-x-1/2 overflow-hidden rounded-md border px-2.5 py-1 font-mono text-xs font-semibold tracking-wide text-ellipsis whitespace-nowrap backdrop-blur ${LABEL_TONE_CLASS[labelTone]}`}
        >
          {label}
        </span>
      )}
    </div>
  )
}
