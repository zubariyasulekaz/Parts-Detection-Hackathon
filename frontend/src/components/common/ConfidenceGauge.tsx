import { useCountUp } from '@/hooks/useCountUp'

interface ConfidenceGaugeProps {
  /** 0–1 */
  value: number
  size?: number
  tone?: 'accent' | 'success' | 'warning'
  label: string
  className?: string
}

const TONE_VAR: Record<NonNullable<ConfidenceGaugeProps['tone']>, string> = {
  accent: 'var(--color-accent)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
}

/**
 * Custom radial-arc readout for confidence/similarity scores — used in
 * place of plain percentage text at the moments that matter most, so the
 * score reads as measured data rather than a marketing stat.
 */
export function ConfidenceGauge({ value, size = 72, tone = 'accent', label, className = '' }: ConfidenceGaugeProps) {
  const clamped = Math.min(Math.max(value, 0), 1)
  const animated = useCountUp(clamped)
  const strokeWidth = Math.max(4, size * 0.09)
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - animated)
  const center = size / 2

  return (
    <div
      role="img"
      aria-label={`${label}: ${Math.round(clamped * 100)}%`}
      className={`relative inline-flex shrink-0 items-center justify-center ${className}`}
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden="true">
        <circle cx={center} cy={center} r={radius} fill="none" stroke="var(--color-surface-3)" strokeWidth={strokeWidth} />
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={TONE_VAR[tone]}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <span className="absolute font-mono text-sm font-bold text-foreground" aria-hidden="true">
        {Math.round(animated * 100)}%
      </span>
    </div>
  )
}
