import { ProductThumbnail } from '@/components/common/ProductThumbnail'
import { Tilt3D } from '@/components/common/Tilt3D'
import type { Product } from '@/types/product'

interface AlternativeProductCardProps {
  product: Product
  onView: (sku: string) => void
}

export function AlternativeProductCard({ product, onView }: AlternativeProductCardProps) {
  return (
    <Tilt3D
      intensity="subtle"
      near
      glare
      sceneClassName="h-full"
      className="shadow-depth group flex h-full flex-col overflow-hidden rounded-xl border border-border-strong bg-surface hover:shadow-depth-lift"
    >
      <ProductThumbnail category={product.category} images={product.images} className="aspect-4/3" />
      <div className="flex flex-1 flex-col gap-1 p-4">
        <span className="text-xs font-semibold tracking-wide text-muted uppercase">{product.brand}</span>
        <span className="text-sm font-semibold text-foreground">{product.productName}</span>
        <span className="font-mono text-xs text-subtle">
          {product.sku} · {product.category}
        </span>
        <button
          type="button"
          onClick={() => onView(product.sku)}
          className="mt-3 rounded-lg border border-border-strong px-3 py-2 text-xs font-semibold text-foreground transition-colors hover:border-accent/50 hover:text-accent-hover"
        >
          View Product
        </button>
      </div>
    </Tilt3D>
  )
}
