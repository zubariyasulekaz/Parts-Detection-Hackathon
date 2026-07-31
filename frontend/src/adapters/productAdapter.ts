import type { ProductResponseDTO, VehicleCompatibilityDTO } from '@/types/api'
import type { Product, VehicleCompatibility } from '@/types/product'

function adaptVehicleCompatibility(dto: VehicleCompatibilityDTO): VehicleCompatibility {
  // The backend only models a single `year`, not a range, and has no `engine`
  // field yet — a range/engine would require a catalog schema change.
  return {
    make: dto.make,
    model: dto.model,
    yearStart: dto.year,
    yearEnd: dto.year,
  }
}

export function adaptProduct(dto: ProductResponseDTO): Product {
  return {
    sku: dto.sku,
    productName: dto.product_name,
    brand: dto.brand,
    category: dto.category,
    description: dto.description ?? '',
    images: dto.image_paths,
    replacementSku: dto.replacement_sku,
    alternativeSkus: dto.alternative_skus,
    accessorySkus: dto.accessory_skus,
    compatibleVehicles: dto.compatible_vehicles.map(adaptVehicleCompatibility),
  }
}
