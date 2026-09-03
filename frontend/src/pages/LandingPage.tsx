import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { HeroPartStage } from '@/components/landing/HeroPartStage'
import { HeroSection } from '@/components/landing/HeroSection'
import { ImageUploadZone } from '@/components/landing/ImageUploadZone'
import { PipelineStrip } from '@/components/landing/PipelineStrip'
import { Tilt3D } from '@/components/common/Tilt3D'
import { AmbientBackground } from '@/components/layout/AmbientBackground'
import { PageContainer } from '@/components/layout/PageContainer'
import { useIdentification } from '@/context/IdentificationContext'
import { useRotatingIndex } from '@/hooks/useRotatingIndex'
import { getSampleImageFile, PART_SAMPLES } from '@/services/sampleImage'
import { ALLOWED_IMAGE_MIME_TYPES, validateImageFile } from '@/services/uploadPolicy'

function formatFileSize(bytes: number): string {
  const megabytes = bytes / (1024 * 1024)
  return megabytes >= 1 ? `${megabytes.toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`
}

export function LandingPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { setPendingUpload } = useIdentification()

  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isDragActive, setIsDragActive] = useState(false)
  const [isSampleLoading, setIsSampleLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // Held here, not inside the upload zone: "Try Sample Image" has to submit
  // whichever sample is on screen at the moment it's clicked.
  const [activeSampleIndex, setActiveSampleIndex] = useRotatingIndex(PART_SAMPLES.length, {
    paused: Boolean(previewUrl) || isSampleLoading,
  })
  const activeSample = PART_SAMPLES[activeSampleIndex]

  useEffect(() => {
    if (location.hash === '#how-it-works') {
      document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [location.hash])

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  function acceptFile(candidate: File) {
    const validation = validateImageFile(candidate)
    if (!validation.valid) {
      setError(validation.error ?? 'This file could not be uploaded.')
      return
    }
    setError(null)
    setFile(candidate)
    setPreviewUrl(URL.createObjectURL(candidate))
  }

  function handleBrowseClick() {
    inputRef.current?.click()
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0]
    if (selected) acceptFile(selected)
    event.target.value = ''
  }

  function handleRemove() {
    setFile(null)
    setPreviewUrl(null)
    setError(null)
  }

  function goIdentify(target: File, isSample: boolean) {
    setPendingUpload(target, isSample)
    navigate('/identify')
  }

  async function handleTrySample() {
    setIsSampleLoading(true)
    try {
      const sampleFile = await getSampleImageFile(activeSample)
      acceptFile(sampleFile)
      goIdentify(sampleFile, true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load the sample image.')
    } finally {
      setIsSampleLoading(false)
    }
  }

  return (
    <div>
      <section className="relative overflow-hidden border-b border-border">
        <AmbientBackground />

        {/* The rotor is the hero's backdrop now, not an object beside the card:
            centred left-of-middle so it sits behind the headline *and* the
            upload zone, with both rendered on top at z-10. Click-through, so it
            never intercepts a click meant for the drop zone. Large viewports
            only - below `xl` the columns collapse and it would sit directly
            under body copy at full strength. */}
        <HeroPartStage className="pointer-events-none absolute top-1/2 left-[46%] z-0 hidden h-152 w-152 -translate-x-1/2 -translate-y-1/2 opacity-70 xl:block" />

        {/* Readability scrim over the copy column. Body text is low-contrast by
            design (`--color-muted` on a dark base) and machined metal is a
            mid-tone, so the two collide exactly where the paragraph crosses the
            disc. Darkening the whole rotor would fix the text and lose the
            effect; a left-anchored wash keeps the copy on a solid base while
            leaving the right half of the rotor fully exposed. */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 left-0 z-1 hidden w-[54%] bg-linear-to-r from-background via-background/88 to-transparent xl:block"
        />

        <PageContainer className="relative z-10 py-10 lg:py-14">
          {/* The upload card is capped rather than taking a full half: at an
              even split its left edge sits ~190px from the headline, which is
              not enough room for the rotor to be anything but occluded. Capping
              it opens a ~340px lane between the two columns for the 3D object,
              and the card is still the largest thing on the page. */}
          <div className="grid gap-10 lg:grid-cols-[1fr_minmax(0,28rem)] lg:items-center lg:gap-12">
            <HeroSection
              onUploadClick={handleBrowseClick}
              onTrySample={handleTrySample}
              isSampleLoading={isSampleLoading}
              sampleCategory={activeSample?.category}
            />

            <div className="animate-pop-in relative" style={{ animationDelay: '150ms' }}>
              <input
                ref={inputRef}
                type="file"
                accept={ALLOWED_IMAGE_MIME_TYPES.join(',')}
                onChange={handleInputChange}
                className="sr-only"
                aria-hidden="true"
                tabIndex={-1}
              />
              {/* `subtle` deliberately: this is the page's primary control, and
                  a control that swings under the cursor is a control that's
                  harder to click. Enough tilt to lift it off the page, not
                  enough to move the drop target out from under a file. */}
              <Tilt3D intensity="subtle" glare className="rounded-2xl shadow-depth">
                <ImageUploadZone
                  previewUrl={previewUrl}
                  fileSizeLabel={file ? formatFileSize(file.size) : undefined}
                  error={error}
                  isDragActive={isDragActive}
                  samples={PART_SAMPLES}
                  activeSampleIndex={activeSampleIndex}
                  onSelectSample={setActiveSampleIndex}
                  onDragActiveChange={setIsDragActive}
                  onFileDropped={acceptFile}
                  onBrowseClick={handleBrowseClick}
                  onRemove={handleRemove}
                  onIdentify={() => file && goIdentify(file, false)}
                />
              </Tilt3D>
            </div>
          </div>
        </PageContainer>
      </section>

      <section id="how-it-works" className="border-b border-border bg-surface/40 py-14">
        <PageContainer>
          <PipelineStrip />
        </PageContainer>
      </section>
    </div>
  )
}
