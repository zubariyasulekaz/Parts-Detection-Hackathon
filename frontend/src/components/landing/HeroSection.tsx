import { Barcode, Car, ScanSearch } from 'lucide-react'
import { CapabilityBadge } from './CapabilityBadge'

interface HeroSectionProps {
  onUploadClick: () => void
  onTrySample: () => void
  isSampleLoading: boolean
  /** Category of the sample currently on screen — named on the button so the click is predictable. */
  sampleCategory?: string
}

export function HeroSection({ onUploadClick, onTrySample, isSampleLoading, sampleCategory }: HeroSectionProps) {
  return (
    <div className="flex flex-col gap-5">
      <span
        style={{ animationDelay: '0ms' }}
        className="animate-fade-slide-up inline-flex w-fit items-center gap-2 rounded-full border border-accent/25 bg-accent/10 px-3 py-1 text-xs font-bold tracking-[0.2em] text-accent-soft uppercase"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-accent-soft" />
        Visual Catalog Intelligence
      </span>

      <h1
        style={{ animationDelay: '90ms' }}
        className="animate-fade-slide-up text-4xl leading-[1.1] font-extrabold tracking-tight text-foreground sm:text-5xl"
      >
        Identify the <span className="text-gradient-accent">Right Part.</span>
        <br />
        From a Single Image.
      </h1>

      <p style={{ animationDelay: '180ms' }} className="animate-fade-slide-up max-w-md text-base leading-relaxed text-muted">
        Upload a part photo to identify the closest catalog SKU, validate compatibility, and discover replacements and
        related products.
      </p>

      <div style={{ animationDelay: '270ms' }} className="animate-fade-slide-up flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onUploadClick}
          className="shadow-glow-accent rounded-lg bg-linear-to-b from-accent-hover to-accent px-6 py-3.5 text-sm font-semibold text-white transition-transform hover:-translate-y-0.5 active:translate-y-0"
        >
          Upload Part Image
        </button>
        <button
          type="button"
          onClick={onTrySample}
          disabled={isSampleLoading}
          className="rounded-lg border border-border-strong bg-surface-2 px-6 py-3.5 text-sm font-semibold text-foreground transition-colors hover:border-accent/50 hover:text-accent-soft disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSampleLoading ? 'Preparing Sample…' : sampleCategory ? `Try Sample: ${sampleCategory}` : 'Try Sample Image'}
        </button>
      </div>

      <div style={{ animationDelay: '360ms' }} className="animate-fade-slide-up flex flex-wrap gap-x-6 gap-y-2">
        <CapabilityBadge icon={ScanSearch} label="AI Category Detection" />
        <CapabilityBadge icon={Barcode} label="Catalog SKU Matching" />
        <CapabilityBadge icon={Car} label="Compatibility Intelligence" />
      </div>
    </div>
  )
}
