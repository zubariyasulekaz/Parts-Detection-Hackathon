import type { Product } from '@/types/product'

/**
 * Mock catalog used when VITE_API_MODE=mock. Shaped identically to the
 * post-adapter `Product` domain type so catalogService can serve it (and
 * a live `ProductResponse` payload) through the exact same interface.
 *
 * Only src/services and src/mocks should ever import this file.
 */
export const MOCK_PRODUCTS: Product[] = [
  // --- Exhaust Manifold ---------------------------------------------------
  {
    sku: 'EXM001',
    productName: 'Exhaust Manifold Assembly - Driver Side, Cast Iron',
    brand: 'Walker Exhaust',
    category: 'Exhaust Manifold',
    description:
      'Direct-fit cast iron exhaust manifold assembly for the driver-side bank. Includes gasket mounting surface machined to OE tolerances and a heat-resistant coating rated for sustained high-temperature operation.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"material": "cast-iron", "manifold_style": "oem-manifold"},
    images: [],
    replacementSku: 'EXM001R',
    alternativeSkus: ['EXM002', 'EXM003'],
    accessorySkus: ['ACC-GSK-401', 'ACC-STUD-118', 'ACC-HS-220'],
    compatibleVehicles: [
      { make: 'Ford', model: 'F-150', yearStart: 2015, yearEnd: 2020 },
      { make: 'Ford', model: 'Expedition', yearStart: 2011, yearEnd: 2014 },
      { make: 'Lincoln', model: 'Navigator', yearStart: 2011, yearEnd: 2014 },
    ],
  },
  {
    sku: 'EXM001R',
    productName: 'Exhaust Manifold Assembly - Driver Side, Cast Iron (Revised)',
    brand: 'Walker Exhaust',
    category: 'Exhaust Manifold',
    description:
      'Second-generation revision of EXM001 with a reinforced flange to reduce stud-hole cracking under thermal cycling. Direct OE replacement, no modification required.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"material": "cast-iron", "manifold_style": "oem-manifold"},
    images: [],
    replacementSku: null,
    alternativeSkus: ['EXM002', 'EXM003'],
    accessorySkus: ['ACC-GSK-401', 'ACC-STUD-118', 'ACC-HS-220'],
    compatibleVehicles: [
      { make: 'Ford', model: 'F-150', yearStart: 2015, yearEnd: 2020 },
      { make: 'Ford', model: 'Expedition', yearStart: 2011, yearEnd: 2014 },
    ],
  },
  {
    sku: 'EXM002',
    productName: 'Performance Exhaust Manifold - Stainless Steel',
    brand: 'MagnaFlow',
    category: 'Exhaust Manifold',
    description:
      'Tubular stainless-steel exhaust manifold engineered for improved exhaust flow over the stock cast-iron unit, with a ceramic thermal barrier coating.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"material": "cast-iron", "manifold_style": "oem-manifold"},
    images: [],
    replacementSku: null,
    alternativeSkus: ['EXM001', 'EXM003'],
    accessorySkus: ['ACC-GSK-401', 'ACC-STUD-118'],
    compatibleVehicles: [
      { make: 'Ford', model: 'F-150', yearStart: 2015, yearEnd: 2020 },
      { make: 'Ford', model: 'Mustang GT', yearStart: 2015, yearEnd: 2023 },
    ],
  },
  {
    sku: 'EXM003',
    productName: 'OE Solutions Exhaust Manifold Kit',
    brand: 'Dorman',
    category: 'Exhaust Manifold',
    description:
      'Complete bolt-on kit including manifold, gaskets, and hardware, engineered to resolve a common OE stud-corrosion failure point.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"manifold_style": "oem-manifold"},
    images: [],
    replacementSku: null,
    alternativeSkus: ['EXM001', 'EXM002'],
    accessorySkus: ['ACC-HS-220'],
    compatibleVehicles: [
      { make: 'Ford', model: 'Expedition', yearStart: 2011, yearEnd: 2014 },
      { make: 'Lincoln', model: 'Navigator', yearStart: 2011, yearEnd: 2014 },
    ],
  },
  {
    sku: 'ACC-GSK-401',
    productName: 'Exhaust Manifold Gasket Kit',
    brand: 'Fel-Pro',
    category: 'Gaskets',
    description: 'Multi-layer steel gasket set sized for V8 exhaust manifold installations.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"sold_as": "set", "material": "steel"},
    images: [],
    replacementSku: null,
    alternativeSkus: [],
    accessorySkus: [],
    compatibleVehicles: [],
  },
  {
    sku: 'ACC-STUD-118',
    productName: 'Exhaust Manifold Mounting Stud Kit',
    brand: 'Dorman',
    category: 'Hardware',
    description: 'Heat-resistant stud and locking-nut kit for exhaust manifold reinstallation.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {},
    images: [],
    replacementSku: null,
    alternativeSkus: [],
    accessorySkus: [],
    compatibleVehicles: [],
  },
  {
    sku: 'ACC-HS-220',
    productName: 'Exhaust Manifold Heat Shield',
    brand: 'Dorman',
    category: 'Heat Shields',
    description: 'Stamped-steel heat shield that protects adjacent wiring and hoses from radiant heat.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"material": "steel"},
    images: [],
    replacementSku: null,
    alternativeSkus: [],
    accessorySkus: [],
    compatibleVehicles: [],
  },

  // --- Brake Pads -----------------------------------------------------------
  {
    sku: 'BP-1042',
    productName: 'QuietCast Ceramic Disc Brake Pad Set - Front',
    brand: 'Bosch',
    category: 'Brake Pads',
    description:
      'Premium ceramic friction compound engineered for low dust and low noise, with integrated wear sensors and OE-matched shims.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"position": "front", "sold_as": "set", "friction_material": "ceramic"},
    images: [],
    replacementSku: 'BP-1058',
    alternativeSkus: ['BP-1043', 'BP-1044'],
    accessorySkus: ['ACC-CAL-330', 'ACC-SENS-210'],
    compatibleVehicles: [
      { make: 'Toyota', model: 'Camry', yearStart: 2018, yearEnd: 2024 },
      { make: 'Toyota', model: 'RAV4', yearStart: 2019, yearEnd: 2024 },
    ],
  },
  {
    sku: 'BP-1058',
    productName: 'QuietCast Ceramic Disc Brake Pad Set - Front (Gen 2)',
    brand: 'Bosch',
    category: 'Brake Pads',
    description: 'Updated friction formulation of BP-1042 with reduced break-in fade.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"position": "front", "sold_as": "set", "friction_material": "ceramic"},
    images: [],
    replacementSku: null,
    alternativeSkus: ['BP-1043', 'BP-1044'],
    accessorySkus: ['ACC-CAL-330', 'ACC-SENS-210'],
    compatibleVehicles: [{ make: 'Toyota', model: 'Camry', yearStart: 2018, yearEnd: 2024 }],
  },
  {
    sku: 'BP-1043',
    productName: 'Professional Ceramic Brake Pad Set - Front',
    brand: 'ACDelco',
    category: 'Brake Pads',
    description: 'OE-style ceramic pad set with chamfered and slotted design to reduce noise and vibration.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"position": "front", "sold_as": "set", "friction_material": "ceramic"},
    images: [],
    replacementSku: null,
    alternativeSkus: ['BP-1042', 'BP-1044'],
    accessorySkus: ['ACC-CAL-330'],
    compatibleVehicles: [
      { make: 'Toyota', model: 'Camry', yearStart: 2018, yearEnd: 2024 },
      { make: 'Honda', model: 'Accord', yearStart: 2018, yearEnd: 2022 },
    ],
  },
  {
    sku: 'BP-1044',
    productName: 'Ceramic Performance Brake Pad Set - Front',
    brand: 'Brembo',
    category: 'Brake Pads',
    description: 'Track-oriented ceramic compound with a higher friction coefficient across a wide temperature range.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"position": "front", "sold_as": "set", "friction_material": "ceramic"},
    images: [],
    replacementSku: null,
    alternativeSkus: ['BP-1042', 'BP-1043'],
    accessorySkus: ['ACC-CAL-330', 'ACC-SENS-210'],
    compatibleVehicles: [{ make: 'Honda', model: 'Accord', yearStart: 2018, yearEnd: 2022 }],
  },
  {
    sku: 'ACC-CAL-330',
    productName: 'Brake Caliper Hardware Kit',
    brand: 'Carlson',
    category: 'Hardware',
    description: 'Stainless abutment clips and guide pin bushings for a quiet, properly seated pad installation.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"material": "stainless-steel"},
    images: [],
    replacementSku: null,
    alternativeSkus: [],
    accessorySkus: [],
    compatibleVehicles: [],
  },
  {
    sku: 'ACC-SENS-210',
    productName: 'Brake Pad Wear Sensor',
    brand: 'ATE',
    category: 'Sensors',
    description: 'Replacement wear-indicator sensor wired to the factory brake-pad-life warning circuit.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {},
    images: [],
    replacementSku: null,
    alternativeSkus: [],
    accessorySkus: [],
    compatibleVehicles: [],
  },

  // --- Oil Filter -------------------------------------------------------------
  {
    sku: 'OF-3978',
    productName: 'Engine Oil Filter - Spin-On',
    brand: 'Mahle',
    category: 'Oil Filter',
    description: 'Full-flow spin-on filter with a silicone anti-drain-back valve and 99% filtration efficiency at 20 microns.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"filter_style": "spin-on"},
    images: [],
    replacementSku: 'OF-45011',
    alternativeSkus: ['OF-45023'],
    accessorySkus: ['ACC-DRAIN-05'],
    compatibleVehicles: [
      { make: 'Honda', model: 'Civic', yearStart: 2016, yearEnd: 2021 },
      { make: 'Honda', model: 'CR-V', yearStart: 2017, yearEnd: 2022 },
    ],
  },
  {
    sku: 'OF-45011',
    productName: 'Engine Oil Filter - Spin-On (Extended Life)',
    brand: 'Bosch',
    category: 'Oil Filter',
    description: 'Extended-service-interval filter with a synthetic-blend media rated for up to 10,000 miles.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"filter_style": "spin-on"},
    images: [],
    replacementSku: null,
    alternativeSkus: ['OF-3978', 'OF-45023'],
    accessorySkus: ['ACC-DRAIN-05'],
    compatibleVehicles: [{ make: 'Honda', model: 'Civic', yearStart: 2016, yearEnd: 2021 }],
  },
  {
    sku: 'OF-45023',
    productName: 'Engine Oil Filter - Spin-On',
    brand: 'Fram',
    category: 'Oil Filter',
    description: 'Standard-service spin-on filter with a metal end cap and silicone valve.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"filter_style": "spin-on"},
    images: [],
    replacementSku: null,
    alternativeSkus: ['OF-3978', 'OF-45011'],
    accessorySkus: [],
    compatibleVehicles: [{ make: 'Honda', model: 'CR-V', yearStart: 2017, yearEnd: 2022 }],
  },
  {
    sku: 'ACC-DRAIN-05',
    productName: 'Oil Drain Plug Gasket (10-Pack)',
    brand: 'Dorman',
    category: 'Hardware',
    description: 'Crush washers sized for the factory drain plug, sold as a service pack.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {},
    images: [],
    replacementSku: null,
    alternativeSkus: [],
    accessorySkus: [],
    compatibleVehicles: [],
  },

  // --- Air Filter -------------------------------------------------------------
  {
    sku: 'AF-2210',
    productName: 'Engine Air Filter - Panel',
    brand: 'Denso',
    category: 'Air Filter',
    description: 'Pleated-paper panel filter sized for the factory airbox, rated for 15,000-mile service intervals.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"filter_shape": "panel"},
    images: [],
    replacementSku: null,
    alternativeSkus: ['AF-2211'],
    accessorySkus: [],
    compatibleVehicles: [
      { make: 'Toyota', model: 'Corolla', yearStart: 2020, yearEnd: 2024 },
      { make: 'Toyota', model: 'Camry', yearStart: 2018, yearEnd: 2024 },
    ],
  },
  {
    sku: 'AF-2211',
    productName: 'High-Flow Engine Air Filter - Panel',
    brand: 'K&N',
    category: 'Air Filter',
    description: 'Reusable cotton-gauze panel filter engineered for increased airflow over a paper-media equivalent.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"filter_shape": "panel"},
    images: [],
    replacementSku: null,
    alternativeSkus: ['AF-2210'],
    accessorySkus: [],
    compatibleVehicles: [{ make: 'Toyota', model: 'Corolla', yearStart: 2020, yearEnd: 2024 }],
  },

  // --- Spark Plug ---------------------------------------------------------------
  {
    sku: 'SP-6610',
    productName: 'Iridium Long-Life Spark Plug',
    brand: 'NGK',
    category: 'Spark Plug',
    description: 'Fine-wire iridium center electrode rated for 100,000-mile service intervals under normal use.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {},
    images: [],
    replacementSku: null,
    alternativeSkus: ['SP-6611'],
    accessorySkus: ['ACC-COIL-118'],
    compatibleVehicles: [
      { make: 'Ford', model: 'F-150', yearStart: 2015, yearEnd: 2020 },
      { make: 'Ford', model: 'Mustang GT', yearStart: 2015, yearEnd: 2023 },
    ],
  },
  {
    sku: 'SP-6611',
    productName: 'Platinum Spark Plug',
    brand: 'Denso',
    category: 'Spark Plug',
    description: 'Platinum-tipped electrode for reliable ignition across standard service intervals.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {},
    images: [],
    replacementSku: null,
    alternativeSkus: ['SP-6610'],
    accessorySkus: ['ACC-COIL-118'],
    compatibleVehicles: [{ make: 'Ford', model: 'F-150', yearStart: 2015, yearEnd: 2020 }],
  },
  {
    sku: 'ACC-COIL-118',
    productName: 'Ignition Coil Pack',
    brand: 'Delphi',
    category: 'Ignition',
    description: 'Direct-fit ignition coil, commonly replaced alongside spark plugs during tune-up service.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {},
    images: [],
    replacementSku: null,
    alternativeSkus: [],
    accessorySkus: [],
    compatibleVehicles: [],
  },

  // --- Cabin Filter -----------------------------------------------------------
  {
    sku: 'CF-1180',
    productName: 'Cabin Air Filter - Activated Carbon',
    brand: 'Mahle',
    category: 'Cabin Filter',
    description: 'Activated-carbon media filters particulates and reduces odor intrusion through the HVAC intake.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {},
    images: [],
    replacementSku: null,
    alternativeSkus: ['CF-1181'],
    accessorySkus: [],
    compatibleVehicles: [
      { make: 'Honda', model: 'Civic', yearStart: 2016, yearEnd: 2021 },
      { make: 'Honda', model: 'Accord', yearStart: 2018, yearEnd: 2022 },
    ],
  },
  {
    sku: 'CF-1181',
    productName: 'Cabin Air Filter - Standard Particulate',
    brand: 'Bosch',
    category: 'Cabin Filter',
    description: 'Standard particulate media sized for the factory HVAC housing.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {},
    images: [],
    replacementSku: null,
    alternativeSkus: ['CF-1180'],
    accessorySkus: [],
    compatibleVehicles: [{ make: 'Honda', model: 'Civic', yearStart: 2016, yearEnd: 2021 }],
  },

  // --- Shock Absorbers ---------------------------------------------------------
  {
    sku: 'SA-2210',
    productName: 'Excel-G Gas Shock Absorber - Rear',
    brand: 'KYB',
    category: 'Shock Absorbers',
    description:
      'Twin-tube, gas-charged shock absorber engineered to restore factory ride control and damping performance.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"position": "rear"},
    images: [],
    replacementSku: null,
    alternativeSkus: ['SA-2211'],
    accessorySkus: ['ACC-MOUNT-118', 'ACC-BOOT-44'],
    compatibleVehicles: [
      { make: 'Toyota', model: 'Camry', yearStart: 2018, yearEnd: 2024 },
      { make: 'Honda', model: 'Accord', yearStart: 2018, yearEnd: 2022 },
    ],
  },
  {
    sku: 'SA-2211',
    productName: 'OESpectrum Shock Absorber - Rear',
    brand: 'Monroe',
    category: 'Shock Absorbers',
    description:
      'OE-style shock absorber with a spectrum valving system tuned to match original ride and handling characteristics.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {"position": "rear"},
    images: [],
    replacementSku: null,
    alternativeSkus: ['SA-2210'],
    accessorySkus: ['ACC-MOUNT-118'],
    compatibleVehicles: [{ make: 'Toyota', model: 'Camry', yearStart: 2018, yearEnd: 2024 }],
  },
  {
    sku: 'ACC-MOUNT-118',
    productName: 'Strut Mount Kit',
    brand: 'Moog',
    category: 'Hardware',
    description: 'Upper strut mount with an integrated bearing, typically replaced alongside the shock or strut.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {},
    images: [],
    replacementSku: null,
    alternativeSkus: [],
    accessorySkus: [],
    compatibleVehicles: [],
  },
  {
    sku: 'ACC-BOOT-44',
    productName: 'Shock Absorber Dust Boot Kit',
    brand: 'Moog',
    category: 'Hardware',
    description: 'Protective dust boot and bump stop kit that shields the shock shaft from debris and road grime.',
    // Synthetic demo catalog - these SKUs have no real part numbers.
    manufacturerPartNumber: null,
    attributes: {},
    images: [],
    replacementSku: null,
    alternativeSkus: [],
    accessorySkus: [],
    compatibleVehicles: [],
  },
]

export function findMockProduct(sku: string): Product | undefined {
  return MOCK_PRODUCTS.find((product) => product.sku === sku)
}
