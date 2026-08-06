import { ProductThumbnail } from '@/components/common/ProductThumbnail'
import type { Product } from '@/types/product'

interface AccessoryCardProps {
  product: Product
  onView: (sku: string) => void
}

export function AccessoryCard({ product, onView }: AccessoryCardProps) {
  return (
    <div className="shadow-card group flex flex-col overflow-hidden rounded-xl border border-border-strong bg-surface transition-all hover:-translate-y-0.5 hover:shadow-glow-accent">
      <ProductThumbnail category={product.category} images={product.images} className="aspect-4/3" />
      <div className="flex flex-1 flex-col gap-1 p-4">
        <span className="text-xs font-semibold tracking-wide text-accent-hover uppercase">{product.category}</span>
        <span className="text-sm font-semibold text-foreground">{product.productName}</span>
        <span className="font-mono text-xs text-subtle">
          {product.sku} · {product.brand}
        </span>
        <button
          type="button"
          onClick={() => onView(product.sku)}
          className="mt-3 rounded-lg border border-border-strong px-3 py-2 text-xs font-semibold text-foreground transition-colors hover:border-accent/50 hover:text-accent-hover"
        >
          View Product
        </button>
      </div>
    </div>
  )
}
