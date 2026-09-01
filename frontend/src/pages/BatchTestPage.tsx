import { FolderOpen, Images, Loader2, Square } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AmbientBackground } from '@/components/layout/AmbientBackground'
import { PageContainer } from '@/components/layout/PageContainer'
import { BatchMatchRow, type BatchRowState } from '@/components/batch/BatchMatchRow'
import { useIdentification } from '@/context/IdentificationContext'
import { identify } from '@/services/identificationService'
import { IMAGE_EXTENSIONS, isImageFile, resolveExpectedSku, tally, verdictFor } from '@/services/batchTest'

/**
 * Runs a folder of photographs through the search, one after another.
 *
 * A single upload is the easiest thing in the world to cherry-pick, and every
 * image-search demo shows one. A folder deliberately mixed with worn parts,
 * phone snaps, awkward angles and a couple of easy ones shows the range - which
 * is both a fairer demonstration and the fastest way to see what a change to
 * the index actually did.
 *
 * Sequential rather than parallel: the search runs on CPU, and fifteen
 * concurrent requests would queue anyway while making each one slower. Watching
 * them land one at a time also reads better in a room than a spinner that sits
 * still for thirty seconds.
 */
export function BatchTestPage() {
  const navigate = useNavigate()
  const { setPendingUpload, runIdentification } = useIdentification()
  const [rows, setRows] = useState<BatchRowState[]>([])
  const [running, setRunning] = useState(false)
  /** The row whose full result is being opened - one at a time. */
  const [openingId, setOpeningId] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const filesInputRef = useRef<HTMLInputElement>(null)
  const filesRef = useRef<Map<string, File>>(new Map())
  // Set when the user stops a run, read between images so an in-flight search
  // finishes rather than being abandoned half way.
  const cancelledRef = useRef(false)

  // React does not forward `webkitdirectory` from JSX - it is not in its known
  // attribute list and is dropped silently, leaving an ordinary file picker
  // that cannot select a folder at all. Setting it on the node is the only way.
  const [canPickFolder, setCanPickFolder] = useState(true)
  useEffect(() => {
    const node = inputRef.current
    if (!node) return
    node.setAttribute('webkitdirectory', '')
    node.setAttribute('directory', '')
    // Firefox and older Safari expose neither, and clicking the button would
    // open a plain file dialog while the label promised a folder.
    setCanPickFolder('webkitdirectory' in node)
  }, [])

  // Object URLs outlive the render that made them, so they have to be released
  // by hand - fifteen full-size photographs held open is real memory.
  const urlsRef = useRef<string[]>([])
  useEffect(() => {
    const urls = urlsRef.current
    return () => urls.forEach((url) => URL.revokeObjectURL(url))
  }, [])

  const totals = tally(rows.filter((row) => row.status === 'done').map((row) => row.verdict))
  const finished = rows.filter((row) => row.status === 'done' || row.status === 'failed').length

  const updateRow = useCallback((id: string, patch: Partial<BatchRowState>) => {
    setRows((current) => current.map((row) => (row.id === id ? { ...row, ...patch } : row)))
  }, [])

  async function handleFolder(fileList: FileList | null) {
    if (!fileList) return
    const files = Array.from(fileList).filter(isImageFile)
    if (!files.length) {
      window.alert('That folder has no images in it. Pick one containing .jpg or .png files.')
      return
    }

    urlsRef.current.forEach((url) => URL.revokeObjectURL(url))
    urlsRef.current = []
    filesRef.current = new Map()

    const next: BatchRowState[] = files.map((file, index) => {
      const previewUrl = URL.createObjectURL(file)
      urlsRef.current.push(previewUrl)
      const id = `${index}-${file.name}`
      filesRef.current.set(id, file)
      return {
        id,
        fileName: file.name,
        previewUrl,
        status: 'waiting',
        expectedSku: null,
        verdict: 'unscored',
        result: null,
        error: null,
      }
    })

    setRows(next)
    cancelledRef.current = false
    setRunning(true)

    for (const row of next) {
      if (cancelledRef.current) {
        updateRow(row.id, { status: 'failed', error: 'Stopped before this photo ran.' })
        continue
      }
      const file = filesRef.current.get(row.id)
      if (!file) continue

      updateRow(row.id, { status: 'running' })
      try {
        // Resolved first so the expected SKU is on screen while the search
        // runs - a viewer can see what the answer should be before it arrives.
        const expectedSku = await resolveExpectedSku(file)
        updateRow(row.id, { expectedSku })

        const result = await identify(file, row.previewUrl)
        updateRow(row.id, {
          status: 'done',
          result,
          verdict: verdictFor(expectedSku, result.candidates.map((candidate) => candidate.sku)),
        })
      } catch (error) {
        updateRow(row.id, {
          status: 'failed',
          error: error instanceof Error ? error.message : 'Search failed.',
        })
      }
    }

    setRunning(false)
  }

  /**
   * Re-runs one photograph through the normal flow and opens the results page,
   * where it gets the full treatment: the comparison hero, all five candidates
   * as cards with their photographs and specifications, the match summary and
   * the guided questions.
   *
   * The search runs *before* navigating, not after. Navigating first lands on
   * the results page while it still has no result, so it renders its "nothing
   * uploaded yet" empty state for three seconds and then pops into the real
   * answer - which reads as a bug. Waiting here costs the same three seconds
   * with a spinner on the button the user just pressed.
   */
  async function openFullResult(row: BatchRowState) {
    const file = filesRef.current.get(row.id)
    if (!file || openingId) return
    setOpeningId(row.id)
    setPendingUpload(file)
    try {
      await runIdentification(file)
      navigate('/results')
    } catch {
      setOpeningId(null)
    }
  }

  return (
    <div className="relative overflow-hidden">
      <AmbientBackground className="opacity-60" />
      <PageContainer className="relative py-14">
        <div className="mx-auto max-w-2xl text-center">
          <span className="text-xs font-bold tracking-[0.2em] text-accent-hover uppercase">Batch test</span>
          <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-foreground">Run a folder of photos</h1>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Pick a folder and every photograph in it is searched in turn. Mix easy shots with worn parts,
            phone snaps and awkward angles - one photograph proves nothing, and the spread is the honest
            picture.
          </p>
          <p className="mt-2 text-xs text-subtle">
            Name a file after its part number, or put it in a folder named after one, and it is marked right
            or wrong automatically. Files that name no product are still searched, just not counted.
          </p>
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          {/* `webkitdirectory` is set on the node in an effect, not here: React
              does not forward it through JSX, so writing it as a prop silently
              produces an ordinary file picker. */}
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={IMAGE_EXTENSIONS.join(',')}
            className="hidden"
            onChange={(event) => {
              void handleFolder(event.target.files)
              event.target.value = ''
            }}
          />
          <input
            ref={filesInputRef}
            type="file"
            multiple
            accept={IMAGE_EXTENSIONS.join(',')}
            className="hidden"
            onChange={(event) => {
              void handleFolder(event.target.files)
              event.target.value = ''
            }}
          />
          {canPickFolder && (
            <button
              type="button"
              disabled={running}
              onClick={() => inputRef.current?.click()}
              className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
            >
              <FolderOpen className="h-4 w-4" aria-hidden="true" />
              Choose a folder
            </button>
          )}
          {/* Folder pickers are Chrome and Edge only, and a folder is awkward
              when the photographs are scattered. Selecting files directly works
              everywhere and scores identically - only the per-SKU folder name
              is lost, which matters solely for part numbers ending in a digit. */}
          <button
            type="button"
            disabled={running}
            onClick={() => filesInputRef.current?.click()}
            className={`inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors disabled:opacity-50 ${
              canPickFolder
                ? 'border border-border-strong text-muted hover:border-accent/50 hover:text-foreground'
                : 'bg-accent text-white hover:bg-accent-hover'
            }`}
          >
            <Images className="h-4 w-4" aria-hidden="true" />
            {canPickFolder ? 'Or pick images' : 'Choose images'}
          </button>
          {running && (
            <button
              type="button"
              onClick={() => {
                cancelledRef.current = true
              }}
              className="inline-flex items-center gap-2 rounded-lg border border-border-strong px-4 py-2.5 text-sm font-semibold text-muted transition-colors hover:text-foreground"
            >
              <Square className="h-3.5 w-3.5" aria-hidden="true" />
              Stop
            </button>
          )}
        </div>

        {rows.length > 0 && (
          <div className="shadow-depth mt-10 rounded-xl border border-border-strong bg-surface p-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-2.5">
                {running && <Loader2 className="h-4 w-4 animate-spin text-accent" aria-hidden="true" />}
                <p className="text-sm font-semibold text-foreground">
                  {running ? `Searching ${finished + 1} of ${rows.length}` : `${rows.length} photographs`}
                </p>
              </div>
              {totals.scored > 0 && (
                <div className="flex flex-wrap items-center gap-5">
                  <span className="text-xs text-muted">
                    <span className="block font-mono text-lg font-bold text-success-soft">
                      {totals.top1}/{totals.scored}
                    </span>
                    exact match
                  </span>
                  <span className="text-xs text-muted">
                    <span className="block font-mono text-lg font-bold text-accent-soft">
                      {totals.top5}/{totals.scored}
                    </span>
                    in the top five
                  </span>
                  {totals.unscored > 0 && (
                    <span className="text-xs text-subtle">
                      <span className="block font-mono text-lg font-bold text-subtle">{totals.unscored}</span>
                      not counted
                    </span>
                  )}
                </div>
              )}
            </div>
            {totals.scored > 0 && !running && (
              <p className="mt-3 border-t border-border pt-3 text-xs leading-relaxed text-subtle">
                Scored against the part number in each filename or folder. A small folder is indicative, not a
                measurement - the catalogue-wide figures on the Architecture page come from thousands of
                held-out queries.
              </p>
            )}
          </div>
        )}

        <div className="mt-6 flex flex-col gap-5">
          {rows.map((row, index) => (
            <BatchMatchRow
              key={row.id}
              row={row}
              index={index}
              opening={openingId === row.id}
              onOpen={openFullResult}
            />
          ))}
        </div>
      </PageContainer>
    </div>
  )
}
