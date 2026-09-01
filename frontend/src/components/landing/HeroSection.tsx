import { Barcode, ScanSearch, ShieldQuestion } from 'lucide-react'
import { CapabilityBadge } from './CapabilityBadge'

interface HeroSectionProps {
  onUploadClick: () => void
  onTrySample: () => void
  isSampleLoading: boolean
  /** Category of the sample currently on screen - named on the button so the click is predictable. */
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
        className="animate-fade-slide-up text-[2.75rem] leading-[1.04] font-bold tracking-tight text-foreground sm:text-6xl"
      >
        Find the part
        <br />
        <span className="text-gradient-accent whitespace-nowrap">without the name</span>.
      </h1>

      {/* Brighter than the usual `text-muted` body colour: this paragraph now
          sits over the hero's 3D backdrop, where muted grey on mid-grey metal
          stops being legible even with the scrim behind it. */}
      <p
        style={{ animationDelay: '180ms' }}
        className="animate-fade-slide-up max-w-md text-base leading-relaxed text-foreground/80"
      >
        Photograph a trailer part you cannot name and get the closest products in the catalog,
        ranked, with how sure it is about each one.
      </p>

      {/* The row is the perspective scene; the buttons rotate inside it. A
          shallow camera (`-near`) because a button is small - at the hero's
          1200px perspective the same few degrees would be invisible. */}
      <div
        style={{ animationDelay: '270ms' }}
        className="animate-fade-slide-up perspective-scene-near flex flex-wrap items-center gap-3"
      >
        <button
          type="button"
          onClick={onUploadClick}
          className="shadow-glow-accent transform-3d rounded-lg bg-linear-to-r from-accent to-[#1fa2a2] px-7 py-3.5 text-sm font-semibold text-white transition-all duration-300 ease-out hover:-translate-y-1 hover:rotate-x-12 hover:shadow-glow-accent-lg active:translate-y-0 active:rotate-x-0 active:duration-75"
        >
          Upload Part Image
        </button>
        <button
          type="button"
          onClick={onTrySample}
          disabled={isSampleLoading}
          className="edge-3d transform-3d rounded-lg border border-border-strong bg-surface-2 px-6 py-3.5 text-sm font-semibold text-foreground transition-all duration-300 ease-out hover:-translate-y-1 hover:rotate-x-12 hover:border-accent/50 hover:text-accent-soft active:translate-y-0 active:rotate-x-0 active:duration-75 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 disabled:hover:rotate-x-0"
        >
          {isSampleLoading ? 'Preparing Sample…' : sampleCategory ? `Try Sample: ${sampleCategory}` : 'Try Sample Image'}
        </button>
      </div>

      {/* Same `max-w-md` as the paragraph above. Without it the badges run the
          full width of the (now wider) text column and the third one crosses
          into the lane the hero's 3D object occupies. */}
      <div style={{ animationDelay: '360ms' }} className="animate-fade-slide-up flex max-w-md flex-wrap gap-x-6 gap-y-2">
        {/* What the system actually does. "Compatibility Intelligence" went
            with the car-parts catalogue: 48.5% of these products are universal
            trailer parts with no vehicle on record, so a compatibility promise
            would be undeliverable on half the range. */}
        <CapabilityBadge icon={ScanSearch} label="Trained on this catalog" />
        <CapabilityBadge icon={Barcode} label="7,510 products searchable" />
        <CapabilityBadge icon={ShieldQuestion} label="Tells you when it's unsure" />
      </div>
    </div>
  )
}
