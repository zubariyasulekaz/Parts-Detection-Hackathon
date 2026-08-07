import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { PageContainer } from '@/components/layout/PageContainer'
import { AccessoryCard } from '@/components/product/AccessoryCard'
import { AlternativeProductCard } from '@/components/product/AlternativeProductCard'
import { CompatibilityTable } from '@/components/product/CompatibilityTable'
import { ProductDetailsTab } from '@/components/product/ProductDetailsTab'
import { ProductHeader } from '@/components/product/ProductHeader'
import { ReplacementCard } from '@/components/product/ReplacementCard'
import { useIdentification } from '@/context/IdentificationContext'
import { getProduct, getRelationships } from '@/services/catalogService'
import type { Product, ProductRelationships } from '@/types/product'

type TabKey = 'details' | 'compatibility' | 'replacement' | 'alternatives' | 'accessories'

const TABS: { key: TabKey; label: string }[] = [
  { key: 'details', label: 'Product Details' },
  { key: 'compatibility', label: 'Compatibility' },
  { key: 'replacement', label: 'Replacement' },
  { key: 'alternatives', label: 'Alternatives' },
  { key: 'accessories', label: 'Accessories' },
]

type LoadStatus = 'loading' | 'success' | 'error'

export function ProductPage() {
  const { sku } = useParams<{ sku: string }>()
  const navigate = useNavigate()
  const { result } = useIdentification()

  const [product, setProduct] = useState<Product | null>(null)
  const [relationships, setRelationships] = useState<ProductRelationships | null>(null)
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabKey>('details')
  // Bumped by Retry so the fetch effect actually re-runs — setting status
  // back to 'loading' alone re-rendered the spinner without refetching.
  const [reloadToken, setReloadToken] = useState(0)

  useEffect(() => {
    if (!sku) return
    let cancelled = false
    setStatus('loading')
    setActiveTab('details')

    Promise.all([getProduct(sku), getRelationships(sku)])
      .then(([productResult, relationshipsResult]) => {
        if (cancelled) return
        setProduct(productResult)
        setRelationships(relationshipsResult)
        setStatus('success')
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Could not load this product.')
        setStatus('error')
      })

    return () => {
      cancelled = true
    }
  }, [sku, reloadToken])

  const cameFromResults = Boolean(result)

  function handleBack() {
    navigate(cameFromResults ? '/results' : '/catalog')
  }

  function goToProduct(targetSku: string) {
    navigate(`/product/${encodeURIComponent(targetSku)}`)
  }

  if (!sku) {
    return (
      <PageContainer className="py-16">
        <EmptyState title="No product specified" description="Choose a product from the catalog or identification results." />
      </PageContainer>
    )
  }

  if (status === 'loading') {
    return (
      <PageContainer className="py-16">
        <LoadingState label="Loading product intelligence…" />
      </PageContainer>
    )
  }

  if (status === 'error' || !product) {
    return (
      <PageContainer className="py-16">
        <ErrorState message={error ?? 'Could not load this product.'} onRetry={() => setReloadToken((token) => token + 1)} />
      </PageContainer>
    )
  }

  return (
    <PageContainer className="py-12">
      <ProductHeader product={product} backLabel={cameFromResults ? 'Back to Results' : 'Back to Catalog'} onBack={handleBack} />

      <div
        role="tablist"
        aria-label="Product Intelligence"
        className="shadow-card mb-8 flex flex-wrap gap-1 rounded-xl border border-border bg-surface p-1"
      >
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition-all ${
              activeTab === tab.key
                ? 'shadow-glow-accent bg-linear-to-b from-accent-hover to-accent text-white'
                : 'text-muted hover:text-foreground'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div role="tabpanel" className="animate-fade-in">
        {activeTab === 'details' && <ProductDetailsTab product={product} />}

        {activeTab === 'compatibility' && <CompatibilityTable vehicles={product.compatibleVehicles} />}

        {activeTab === 'replacement' && (
          <ReplacementCard product={relationships?.replacement ?? null} onView={goToProduct} />
        )}

        {activeTab === 'alternatives' &&
          (relationships && relationships.alternatives.length > 0 ? (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {relationships.alternatives.map((alternative) => (
                <AlternativeProductCard key={alternative.sku} product={alternative} onView={goToProduct} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="No alternatives listed"
              description="There are currently no alternative products linked to this SKU."
            />
          ))}

        {activeTab === 'accessories' &&
          (relationships && relationships.accessories.length > 0 ? (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {relationships.accessories.map((accessory) => (
                <AccessoryCard key={accessory.sku} product={accessory} onView={goToProduct} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="No accessories listed"
              description="There are currently no accessories linked to this SKU."
            />
          ))}
      </div>
    </PageContainer>
  )
}
