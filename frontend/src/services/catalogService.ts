import { fetchProduct, fetchProducts, fetchRecommendations } from '@/api/partpilotApi'
import { adaptProduct } from '@/adapters/productAdapter'
import { findMockProduct, MOCK_PRODUCTS } from '@/mocks/products'
import type { Product, ProductListParams, ProductRelationships } from '@/types/product'

const API_MODE = import.meta.env.VITE_API_MODE

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function matchesQuery(product: Product, query: string): boolean {
  const q = query.trim().toLowerCase()
  if (!q) return true
  return (
    product.productName.toLowerCase().includes(q) ||
    product.sku.toLowerCase().includes(q) ||
    product.brand.toLowerCase().includes(q)
  )
}

export async function getProduct(sku: string): Promise<Product> {
  if (API_MODE === 'live') {
    return adaptProduct(await fetchProduct(sku))
  }
  await delay(220)
  const product = findMockProduct(sku)
  if (!product) {
    throw new Error(`Product ${sku} was not found in the catalog.`)
  }
  return product
}

export async function listProducts(params: ProductListParams = {}): Promise<Product[]> {
  if (API_MODE === 'live') {
    const dtos = await fetchProducts({ category: params.category, brand: params.brand, limit: params.limit ?? 100 })
    const products = dtos.map(adaptProduct)
    return params.query ? products.filter((product) => matchesQuery(product, params.query!)) : products
  }

  await delay(180)
  return MOCK_PRODUCTS.filter((product) => {
    if (params.category && product.category !== params.category) return false
    if (params.brand && product.brand !== params.brand) return false
    if (params.query && !matchesQuery(product, params.query)) return false
    return true
  })
}

export async function getRelationships(sku: string): Promise<ProductRelationships> {
  const product = await getProduct(sku)

  if (API_MODE === 'live') {
    const [recommendation, replacement] = await Promise.all([
      fetchRecommendations(sku),
      product.replacementSku ? getProduct(product.replacementSku).catch(() => null) : Promise.resolve(null),
    ])
    return {
      replacement,
      alternatives: recommendation.alternatives.map(adaptProduct),
      accessories: recommendation.accessories.map(adaptProduct),
    }
  }

  await delay(200)
  const replacement = product.replacementSku ? (findMockProduct(product.replacementSku) ?? null) : null
  const alternatives = product.alternativeSkus
    .map((relatedSku) => findMockProduct(relatedSku))
    .filter((entry): entry is Product => Boolean(entry))
  const accessories = product.accessorySkus
    .map((relatedSku) => findMockProduct(relatedSku))
    .filter((entry): entry is Product => Boolean(entry))

  return { replacement, alternatives, accessories }
}

export function deriveFilterOptions(products: Product[]): { categories: string[]; brands: string[] } {
  return {
    categories: Array.from(new Set(products.map((product) => product.category))).sort(),
    brands: Array.from(new Set(products.map((product) => product.brand))).sort(),
  }
}
