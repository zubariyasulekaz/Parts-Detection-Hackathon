import { ArrowLeft } from 'lucide-react'
import type { Product } from '@/types/product'

interface ProductHeaderProps {
  product: Product
  backLabel: string
  onBack: () => void
}

export function ProductHeader({ product, backLabel, onBack }: ProductHeaderProps) {
  return (
    <div className="mb-8 flex flex-col gap-4">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex w-fit items-center gap-1.5 text-sm font-medium text-muted transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        {backLabel}
      </button>

      <div>
        <p className="text-xs font-semibold tracking-wide text-accent-hover uppercase">{product.brand}</p>
        <h1 className="mt-1 text-2xl font-bold text-foreground">{product.productName}</h1>
        <p className="mt-1 text-sm text-muted">
          SKU <span className="font-mono text-foreground/80">{product.sku}</span> · {product.category}
        </p>
      </div>
    </div>
  )
}
