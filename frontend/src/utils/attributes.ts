/**
 * Display formatting for the catalog's `attributes` bag.
 *
 * Keys and values arrive as slugs (`filter_style`, `semi-metallic`) because they
 * are derived from prose by `scripts/extract_product_attributes.py` and stored
 * as-is. Both the product page and the guided questions render them, so the
 * formatting lives here rather than being written twice and drifting.
 */

/**
 * Hyphens are kept by default - most of these are genuinely hyphenated terms
 * ("semi-metallic", "spin-on"). This map covers the slugs where the hyphen is
 * only joining words and reads wrong left in.
 */
const VALUE_LABELS: Record<string, string> = {
  'strut-assembly': 'Strut assembly',
  'shock-absorber': 'Shock absorber',
  'remote-reservoir': 'Remote reservoir',
  'air-strut': 'Air strut',
  'long-tube-header': 'Long-tube header',
  'shorty-header': 'Shorty header',
  'oem-manifold': 'OEM manifold',
  'direct-injection': 'Direct injection',
  'common-rail': 'Common rail',
  'dual-fuel': 'Dual fuel',
  'unit-injector': 'Unit injector',
  'stainless-steel': 'Stainless steel',
  'cast-iron': 'Cast iron',
  yes: 'Yes',
  no: 'No',
}

const KEY_LABELS: Record<string, string> = {
  primary_colour: 'Colour',
  sold_as: 'Sold as',
  abs_sensor: 'ABS sensor',
  lug_count: 'Wheel studs',
  mpn: 'Part number',
}

/**
 * Attributes that identify nothing, and must never be shown as though they do.
 *
 * `special_order` reads "No" on 10,631 of 10,813 products, so it distinguishes
 * nothing while occupying a chip. `keyword` holds internal cross-reference
 * strings - one product's is "aqua kem, aqua-kem dri, aqua kem dry, aqua kem
 * powder, aqua-kem powder, aqua-kem dry, aqua kem dri", which rendered raw into
 * a candidate card. And `installation_instructions` is a `\fileserver\...`
 * path that must never reach a customer.
 *
 * Lives here because both the product page and the candidate cards render this
 * bag. It was filtered on one and not the other, and the unfiltered side showed
 * a bare "No" chip under every product.
 */
const NON_IDENTIFYING = new Set(['special_order', 'keyword', 'installation_instructions'])

/** The attribute pairs worth showing, in catalogue order. */
export function identifyingAttributes(
  attributes: Record<string, string> | null | undefined,
): [string, string][] {
  return Object.entries(attributes ?? {}).filter(
    ([key, value]) => Boolean(value) && !NON_IDENTIFYING.has(key),
  )
}

/** `filter_style` -> "Filter style". */
export function formatAttributeLabel(key: string): string {
  if (KEY_LABELS[key]) return KEY_LABELS[key]
  const words = key.replace(/[_-]+/g, ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

/** `semi-metallic` -> "Semi-metallic"; `strut-assembly` -> "Strut assembly". */
export function formatAttributeValue(value: string): string {
  return VALUE_LABELS[value] ?? value.charAt(0).toUpperCase() + value.slice(1)
}
