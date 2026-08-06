import { Upload, X } from 'lucide-react'
import { useRef, type DragEvent, type KeyboardEvent } from 'react'
import { ScanFrame } from '@/components/common/ScanFrame'
import type { PartSample } from '@/services/sampleImage'
import { MAX_UPLOAD_SIZE_MB } from '@/services/uploadPolicy'

interface ImageUploadZoneProps {
  previewUrl: string | null
  fileSizeLabel?: string
  error: string | null
  isDragActive: boolean
  /** One sample photo per category the classifier knows; cycled while the zone is empty. */
  samples: PartSample[]
  activeSampleIndex: number
  onSelectSample: (index: number) => void
  onDragActiveChange: (active: boolean) => void
  onFileDropped: (file: File) => void
  onBrowseClick: () => void
  onRemove: () => void
  onIdentify: () => void
}

export function ImageUploadZone({
  previewUrl,
  fileSizeLabel,
  error,
  isDragActive,
  samples,
  activeSampleIndex,
  onSelectSample,
  onDragActiveChange,
  onFileDropped,
  onBrowseClick,
  onRemove,
  onIdentify,
}: ImageUploadZoneProps) {
  const activeSample = samples[activeSampleIndex]

  const dragDepth = useRef(0)

  function handleDragEnter(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    dragDepth.current += 1
    onDragActiveChange(true)
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    dragDepth.current -= 1
    if (dragDepth.current <= 0) {
      dragDepth.current = 0
      onDragActiveChange(false)
    }
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    dragDepth.current = 0
    onDragActiveChange(false)
    const dropped = event.dataTransfer.files?.[0]
    if (dropped) onFileDropped(dropped)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onBrowseClick()
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload a part image. JPG, PNG or WEBP, maximum 10 megabytes."
        onClick={previewUrl ? undefined : onBrowseClick}
        onKeyDown={previewUrl ? undefined : handleKeyDown}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        className={`shadow-glow-accent group relative flex aspect-4/3 w-full flex-col overflow-hidden rounded-2xl border transition-all ${
          isDragActive ? 'border-accent bg-accent/10' : 'border-accent/20 bg-surface'
        } ${previewUrl ? 'cursor-default' : 'cursor-pointer'}`}
      >
        {previewUrl ? (
          <>
            <img src={previewUrl} alt="Uploaded part preview" className="h-full w-full object-contain p-6" />
            <ScanFrame />
            <div className="absolute top-3 right-3 flex gap-2">
              <button
                type="button"
                onClick={onBrowseClick}
                className="rounded-lg border border-border-strong bg-surface/90 px-3 py-1.5 text-xs font-semibold text-foreground backdrop-blur transition-colors hover:border-accent/50"
              >
                Replace
              </button>
              <button
                type="button"
                onClick={onRemove}
                aria-label="Remove uploaded image"
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-border-strong bg-surface/90 text-muted backdrop-blur transition-colors hover:border-danger/50 hover:text-danger"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </>
        ) : (
          <>
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-x-0 top-0 h-2/3 bg-[radial-gradient(ellipse_at_center,rgba(47,128,237,0.22),transparent_70%)]"
            />

            {/* The tile takes the leftover space above the caption block rather
                than being absolutely placed, so it never collides with the copy
                at narrow widths. Every sample renders into that one frame, so
                photos of differing aspect ratios cross-fade in place instead of
                the tile resizing on each rotation. */}
            <div className="relative flex min-h-0 flex-1 items-center justify-center px-6 pt-7 pb-2">
              <div className="animate-float relative h-full w-[66%] max-w-64 rounded-xl border border-white/15 bg-white/95 p-3 shadow-[0_20px_45px_-14px_rgba(0,0,0,0.75)]">
                <div className="relative h-full w-full">
                  {samples.map((sample, index) => (
                    <img
                      key={sample.slug}
                      src={sample.src}
                      alt={index === activeSampleIndex ? `${sample.category} sample photo` : ''}
                      aria-hidden={index !== activeSampleIndex}
                      className={`absolute inset-0 h-full w-full object-contain transition-opacity duration-700 ${
                        index === activeSampleIndex ? 'opacity-100' : 'opacity-0'
                      }`}
                    />
                  ))}
                </div>
                <div
                  aria-hidden="true"
                  className="animate-scan-line pointer-events-none absolute inset-x-0 top-1/4 h-0.5 bg-linear-to-r from-transparent via-accent-soft to-transparent shadow-[0_0_18px_3px_rgba(47,128,237,0.65)]"
                />
              </div>
            </div>

            {activeSample && (
              <span className="absolute top-3 left-3 rounded-full border border-accent/30 bg-surface/85 px-2.5 py-1 text-[11px] font-bold tracking-wide text-accent-soft uppercase backdrop-blur">
                Sample · {activeSample.category}
              </span>
            )}

            <div className="relative flex flex-col items-center gap-2 px-6 pb-6 text-center">
              {samples.length > 1 && (
                <div className="flex flex-wrap items-center justify-center">
                  {samples.map((sample, index) => (
                    // Padding, not margin: it makes each dot a ~24px target
                    // without spreading ten of them across the whole card.
                    <button
                      key={sample.slug}
                      type="button"
                      aria-label={`Show the ${sample.category} sample`}
                      aria-current={index === activeSampleIndex}
                      onClick={(event) => {
                        event.stopPropagation()
                        onSelectSample(index)
                      }}
                      className="group/dot p-1.5"
                    >
                      <span
                        className={`block h-1.5 rounded-full transition-all ${
                          index === activeSampleIndex
                            ? 'w-5 bg-accent-soft'
                            : 'w-1.5 bg-border-strong group-hover/dot:bg-muted'
                        }`}
                      />
                    </button>
                  ))}
                </div>
              )}
              <p className="text-sm font-semibold text-foreground">Drop a part image here</p>
              <p className="text-xs text-muted">JPG, PNG or WEBP · Maximum {MAX_UPLOAD_SIZE_MB} MB</p>
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation()
                  onBrowseClick()
                }}
                className="mt-1 inline-flex items-center gap-2 rounded-lg border border-border-strong bg-surface-2 px-4 py-2 text-sm font-semibold text-foreground transition-colors hover:border-accent/50 hover:text-accent-hover"
              >
                <Upload className="h-4 w-4" aria-hidden="true" />
                Browse Files
              </button>
            </div>
          </>
        )}
      </div>

      {previewUrl && !error && (
        <div className="flex items-center justify-between gap-3">
          {fileSizeLabel && <span className="text-xs text-muted">{fileSizeLabel}</span>}
          <button
            type="button"
            onClick={onIdentify}
            className="shadow-glow-accent ml-auto rounded-lg bg-linear-to-b from-accent-hover to-accent px-5 py-2.5 text-sm font-semibold text-white transition-transform hover:-translate-y-0.5 active:translate-y-0"
          >
            Identify Part
          </button>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-danger/30 bg-danger-muted/40 px-4 py-3 text-sm text-danger"
        >
          {error}
        </div>
      )}
    </div>
  )
}
