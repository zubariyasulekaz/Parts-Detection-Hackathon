import { ChevronDown, Download, Loader2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { EXPORT_FORMATS, type ExportFormat } from '@/services/batchExport'

interface ExportMenuProps {
  busy?: boolean
  onExport: (format: ExportFormat) => void
}

/**
 * "Export all", with the format chosen from a menu.
 *
 * Closes on a click anywhere else and on Escape, both of which a menu has to
 * do to avoid becoming a panel that follows the reader around the page. The
 * listener is on `pointerdown` rather than `click` so it fires before a button
 * underneath can act on the same press.
 */
export function ExportMenu({ busy = false, onExport }: ExportMenuProps) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onPointerDown(event: PointerEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false)
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        disabled={busy}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        // The app's primary-action treatment, the same one "View Product"
        // carries, rather than a colour invented for this button.
        className="shadow-glow-accent inline-flex items-center gap-2 rounded-lg bg-linear-to-b from-accent-hover to-accent px-4 py-2 text-xs font-semibold text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60 disabled:shadow-none disabled:brightness-100"
      >
        {busy ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
        ) : (
          <Download className="h-3.5 w-3.5" aria-hidden="true" />
        )}
        {busy ? 'Building…' : 'Export all'}
        <ChevronDown
          className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>

      {open && !busy && (
        // Right-aligned: the button sits at the end of the summary row, and a
        // left-aligned menu would run off the edge on a narrow window.
        <div
          role="menu"
          className="shadow-depth absolute right-0 z-20 mt-1.5 w-56 overflow-hidden rounded-lg border border-border-strong bg-surface py-1"
        >
          {EXPORT_FORMATS.map((format) => (
            <button
              key={format.id}
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false)
                onExport(format.id)
              }}
              className="flex w-full flex-col items-start px-3.5 py-2 text-left transition-colors hover:bg-surface-2"
            >
              <span className="text-xs font-semibold text-foreground">{format.label}</span>
              <span className="text-xs text-subtle">{format.hint}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
