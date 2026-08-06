import { formatAttributeLabel, formatAttributeValue } from '@/utils/attributes'
import type { Product } from '@/types/product'
import { ProductImageGallery } from './ProductImageGallery'

interface ProductDetailsTabProps {
  product: Product
}

export function ProductDetailsTab({ product }: ProductDetailsTabProps) {
  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,360px)_1fr]">
      <ProductImageGallery category={product.category} images={product.images} />

      <div className="flex flex-col gap-6">
        <div>
          <h2 className="text-sm font-bold tracking-wide text-muted uppercase">Description</h2>
          <p className="mt-2 text-sm leading-relaxed text-foreground/90">
            {product.description || 'No description available for this product yet.'}
          </p>
        </div>

        <dl className="shadow-card grid grid-cols-2 gap-5 rounded-xl border border-border bg-surface p-5 sm:grid-cols-4">
          <div>
            <dt className="text-xs tracking-wide text-muted uppercase">SKU</dt>
            <dd className="mt-1 font-mono text-sm font-semibold text-foreground">{product.sku}</dd>
          </div>
          <div>
            <dt className="text-xs tracking-wide text-muted uppercase">Brand</dt>
            <dd className="mt-1 text-sm font-semibold text-foreground">{product.brand}</dd>
          </div>
          <div>
            <dt className="text-xs tracking-wide text-muted uppercase">Part Number</dt>
            <dd className="mt-1 font-mono text-sm font-semibold text-foreground">
              {product.manufacturerPartNumber ?? <span className="text-subtle">Not recorded</span>}
            </dd>
          </div>
          <div>
            <dt className="text-xs tracking-wide text-muted uppercase">Category</dt>
            <dd className="mt-1 text-sm font-semibold text-foreground">{product.category}</dd>
          </div>
          <div>
            <dt className="text-xs tracking-wide text-muted uppercase">Vehicles Listed</dt>
            <dd className="mt-1 text-sm font-semibold text-foreground">{product.compatibleVehicles.length}</dd>
          </div>
        </dl>

        {/* The same facts the results page asks about, shown here so a reader
            can check them against the part in front of them. Keys vary by
            category, so this renders whatever the catalog recorded. */}
        {Object.keys(product.attributes).length > 0 && (
          <div>
            <h2 className="text-sm font-bold tracking-wide text-muted uppercase">Identifying Features</h2>
            <dl className="mt-3 flex flex-wrap gap-2">
              {Object.entries(product.attributes).map(([key, value]) => (
                <div
                  key={key}
                  className="rounded-lg border border-border-strong bg-surface-2 px-3 py-2"
                >
                  <dt className="text-xs tracking-wide text-subtle uppercase">
                    {formatAttributeLabel(key)}
                  </dt>
                  <dd className="mt-0.5 text-sm font-semibold text-foreground">
                    {formatAttributeValue(value)}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>
    </div>
  )
}
