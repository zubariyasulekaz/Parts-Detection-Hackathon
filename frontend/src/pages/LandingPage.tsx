import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { HeroSection } from '@/components/landing/HeroSection'
import { ImageUploadZone } from '@/components/landing/ImageUploadZone'
import { PipelineStrip } from '@/components/landing/PipelineStrip'
import { AmbientBackground } from '@/components/layout/AmbientBackground'
import { PageContainer } from '@/components/layout/PageContainer'
import { useIdentification } from '@/context/IdentificationContext'
import { getSampleImageFile } from '@/services/sampleImage'
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
      const sampleFile = await getSampleImageFile()
      acceptFile(sampleFile)
      goIdentify(sampleFile, true)
    } finally {
      setIsSampleLoading(false)
    }
  }

  return (
    <div>
      <section className="relative overflow-hidden border-b border-border">
        <AmbientBackground />
        <PageContainer className="relative py-10 lg:py-14">
          <div className="grid gap-10 lg:grid-cols-2 lg:items-center lg:gap-12">
            <HeroSection onUploadClick={handleBrowseClick} onTrySample={handleTrySample} isSampleLoading={isSampleLoading} />

            <div className="animate-pop-in" style={{ animationDelay: '150ms' }}>
              <input
                ref={inputRef}
                type="file"
                accept={ALLOWED_IMAGE_MIME_TYPES.join(',')}
                onChange={handleInputChange}
                className="sr-only"
                aria-hidden="true"
                tabIndex={-1}
              />
              <ImageUploadZone
                previewUrl={previewUrl}
                fileSizeLabel={file ? formatFileSize(file.size) : undefined}
                error={error}
                isDragActive={isDragActive}
                onDragActiveChange={setIsDragActive}
                onFileDropped={acceptFile}
                onBrowseClick={handleBrowseClick}
                onRemove={handleRemove}
                onIdentify={() => file && goIdentify(file, false)}
              />
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
