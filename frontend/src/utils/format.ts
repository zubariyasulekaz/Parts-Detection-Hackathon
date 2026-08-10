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

/**
 * Percentage for a *difference* between two scores.
 *
 * `formatPercent` rounds a real 0.4-point gap to "0%", which reads as a bug
 * and, worse, understates the case it appears in: two candidates that close
 * are precisely why confirmation is being asked for. Anything below half a
 * point renders as "<1%" instead of vanishing.
 */
export function formatPercentGap(value: number): string {
  const points = value * 100
  if (points > 0 && points < 0.5) return '<1%'
  return `${Math.round(points)}%`
}

/** 240 -> "240 ms", 1400 -> "1.4 s". */
export function formatSearchTime(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`
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
