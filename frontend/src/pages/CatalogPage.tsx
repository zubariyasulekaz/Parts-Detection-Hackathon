import { Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { PageContainer } from '@/components/layout/PageContainer'
import { AlternativeProductCard } from '@/components/product/AlternativeProductCard'
import { deriveFilterOptions, listProducts, matchesQuery } from '@/services/catalogService'
import type { Product } from '@/types/product'

type LoadStatus = 'loading' | 'success' | 'error'

export function CatalogPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [products, setProducts] = useState<Product[]>([])
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [query, setQuery] = useState(() => searchParams.get('q') ?? '')
  const [category, setCategory] = useState('')
  const [brand, setBrand] = useState('')
  // Bumped by Retry so the fetch effect re-runs without a full page reload.
  const [reloadToken, setReloadToken] = useState(0)

  // Header search sets ?q= and navigates here even when already on this
  // page (e.g. searching again without leaving /catalog), which doesn't
  // remount the component - the state initializer above only runs once, so
  // this effect is what keeps the search box in sync on a repeat search.
  useEffect(() => {
    setQuery(searchParams.get('q') ?? '')
  }, [searchParams])

  useEffect(() => {
    let cancelled = false
    setStatus('loading')
    listProducts({})
      .then((result) => {
        if (cancelled) return
        setProducts(result)
        setStatus('success')
      })
      .catch(() => {
        if (!cancelled) setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [reloadToken])

  const { categories, brands } = useMemo(() => deriveFilterOptions(products), [products])

  const filtered = useMemo(() => {
    return products.filter((product) => {
      if (category && product.category !== category) return false
      if (brand && product.brand !== brand) return false
      if (!matchesQuery(product, query)) return false
      return true
    })
  }, [products, query, category, brand])

  function goToProduct(sku: string) {
    navigate(`/product/${encodeURIComponent(sku)}`)
  }

  return (
    <PageContainer className="py-12">
      <div className="mb-8 max-w-2xl">
        <h1 className="text-2xl font-bold text-foreground">Catalog Search</h1>
        <p className="mt-2 text-sm text-muted">
          Browse the PartPilot catalog directly, or identify a part visually from the landing page.
        </p>
      </div>

      <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-subtle" aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by product name, SKU, or brand"
            aria-label="Search catalog"
            className="w-full rounded-lg border border-border-strong bg-surface py-2.5 pr-3 pl-9 text-sm text-foreground placeholder:text-subtle focus:border-accent focus:ring-2 focus:ring-accent/20 focus:outline-none"
          />
        </div>
        <select
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          aria-label="Filter by category"
          className="rounded-lg border border-border-strong bg-surface px-3 py-2.5 text-sm text-foreground focus:border-accent focus:ring-2 focus:ring-accent/20 focus:outline-none"
        >
          <option value="">All Categories</option>
          {categories.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <select
          value={brand}
          onChange={(event) => setBrand(event.target.value)}
          aria-label="Filter by brand"
          className="rounded-lg border border-border-strong bg-surface px-3 py-2.5 text-sm text-foreground focus:border-accent focus:ring-2 focus:ring-accent/20 focus:outline-none"
        >
          <option value="">All Brands</option>
          {brands.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      {status === 'loading' && <LoadingState label="Loading catalog…" />}

      {status === 'error' && (
        <ErrorState
          message="Could not load the catalog. Please try again."
          onRetry={() => setReloadToken((token) => token + 1)}
        />
      )}

      {status === 'success' && filtered.length === 0 && (
        <EmptyState
          title="No such products available"
          description="Try a different search term or clear the category/brand filters."
        />
      )}

      {status === 'success' && filtered.length > 0 && (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filtered.map((product) => (
            <AlternativeProductCard key={product.sku} product={product} onView={goToProduct} />
          ))}
        </div>
      )}
    </PageContainer>
  )
}
