import { EmptyState } from '@/components/common/EmptyState'
import { PartIllustration } from '@/components/common/PartIllustration'
import type { Product } from '@/types/product'

interface ReplacementCardProps {
  product: Product | null
  onView: (sku: string) => void
}

export function ReplacementCard({ product, onView }: ReplacementCardProps) {
  if (!product) {
    return (
      <EmptyState
        title="No replacement available"
        description="This product does not currently have a listed replacement SKU."
      />
    )
  }

  return (
    <div className="shadow-card flex flex-col gap-5 rounded-xl border border-border bg-surface p-6 sm:flex-row sm:items-center">
      <PartIllustration category={product.category} className="h-32 w-full shrink-0 rounded-lg sm:h-28 sm:w-28" />
      <div className="flex-1">
        <p className="text-xs font-semibold tracking-wide text-muted uppercase">{product.brand}</p>
        <p className="text-base font-semibold text-foreground">{product.productName}</p>
        <p className="mt-1 font-mono text-sm text-muted">{product.sku}</p>
        <p className="mt-2 line-clamp-2 text-sm text-muted">{product.description}</p>
      </div>
      <button
        type="button"
        onClick={() => onView(product.sku)}
        className="shadow-glow-accent shrink-0 rounded-lg bg-linear-to-b from-accent-hover to-accent px-4 py-2.5 text-sm font-semibold text-white transition-transform hover:-translate-y-0.5"
      >
        View Replacement
      </button>
    </div>
  )
}
