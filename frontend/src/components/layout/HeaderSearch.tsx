import { Search } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listProducts, matchesQuery } from '@/services/catalogService'
import type { Product } from '@/types/product'

const RESULT_LIMIT = 6

interface HeaderSearchProps {
  className?: string
  /** Fired after a navigation so callers (e.g. the mobile menu) can close themselves. */
  onNavigate?: () => void
}

/**
 * Live catalog search. Products are loaded once and filtered client-side on
 * every keystroke - the catalog is small enough (56 SKUs) that this is
 * instant with no per-keystroke network round trip, using the same match
 * rule as the Catalog page itself.
 */
export function HeaderSearch({ className = '', onNavigate }: HeaderSearchProps) {
  const navigate = useNavigate()
  const containerRef = useRef<HTMLDivElement>(null)
  const [products, setProducts] = useState<Product[]>([])
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)

  useEffect(() => {
    listProducts({}).then(setProducts).catch(() => setProducts([]))
  }, [])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const results = useMemo(() => {
    if (!query.trim()) return []
    return products.filter((product) => matchesQuery(product, query)).slice(0, RESULT_LIMIT)
  }, [products, query])

  function goToCatalog(term: string) {
    const trimmed = term.trim()
    navigate(trimmed ? `/catalog?q=${encodeURIComponent(trimmed)}` : '/catalog')
    setQuery('')
    setOpen(false)
    onNavigate?.()
  }

  const showDropdown = open && query.trim().length > 0

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          goToCatalog(query)
        }}
        className="relative"
      >
        <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-subtle" aria-hidden="true" />
        <input
          type="search"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          placeholder="Search the catalog…"
          aria-label="Search catalog"
          className="w-full rounded-lg border border-border-strong bg-surface py-2.5 pr-3 pl-9 text-sm text-foreground placeholder:text-subtle focus:border-accent focus:ring-2 focus:ring-accent/20 focus:outline-none"
        />
      </form>

      {showDropdown && (
        <div className="absolute top-full right-0 left-0 z-50 mt-2 max-h-80 overflow-y-auto rounded-lg border border-border bg-surface shadow-lg">
          {results.length === 0 ? (
            <p className="px-4 py-3 text-sm text-muted">No such products available.</p>
          ) : (
            <ul>
              {results.map((product) => (
                <li key={product.sku}>
                  <button
                    type="button"
                    onClick={() => goToCatalog(product.sku)}
                    className="flex w-full flex-col items-start gap-0.5 px-4 py-2.5 text-left transition-colors hover:bg-surface-2"
                  >
                    <span className="text-sm font-medium text-foreground">{product.productName}</span>
                    <span className="text-xs text-muted">
                      {product.sku} · {product.brand}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
