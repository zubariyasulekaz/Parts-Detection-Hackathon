import { ConfidenceGauge } from '@/components/common/ConfidenceGauge'

interface ConfidenceMetricProps {
  label: string
  primary: string
  primaryMono?: boolean
  secondary: string
  gaugeValue: number
  gaugeTone?: 'accent' | 'success' | 'warning'
}

export function ConfidenceMetric({
  label,
  primary,
  primaryMono = false,
  secondary,
  gaugeValue,
  gaugeTone = 'accent',
}: ConfidenceMetricProps) {
  return (
    <div className="flex items-center gap-4">
      <ConfidenceGauge value={gaugeValue} size={56} tone={gaugeTone} label={label} />
      <div className="min-w-0">
        <p className="text-xs font-semibold tracking-wide text-muted uppercase">{label}</p>
        <p className={`mt-1 truncate text-lg font-bold text-foreground ${primaryMono ? 'font-mono' : ''}`}>{primary}</p>
        <p className="font-mono text-xs text-muted">{secondary}</p>
      </div>
    </div>
  )
}
