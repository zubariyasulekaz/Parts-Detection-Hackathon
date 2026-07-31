/** "oil_filter" -> "Oil Filter". Idempotent on already-formatted strings like "Exhaust Manifold". */
export function formatCategoryLabel(raw: string): string {
  return raw
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`
}

export function formatYearRange(yearStart: number, yearEnd: number): string {
  return yearStart === yearEnd ? String(yearStart) : `${yearStart}–${yearEnd}`
}

/** Backend image paths aren't served as static assets yet; only render absolute http(s) URLs. */
export function isDisplayableImageUrl(value: string | undefined): value is string {
  if (!value) return false
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}
