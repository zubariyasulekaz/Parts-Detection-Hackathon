import { getProduct } from './catalogService'

/**
 * Running a whole folder of photographs through the search in one go.
 *
 * One photograph proves nothing - the good ones are easy to pick and every
 * demo shows one. A folder deliberately mixed with worn parts, phone snaps and
 * awkward angles shows the range, which is the only honest way to present an
 * image search to someone who will later use it on their worst photograph.
 *
 * Scoring is optional and self-configuring: a file that names a real SKU gets
 * marked right or wrong, and one that does not is still searched and shown,
 * just uncounted. So a folder can hold a mix without being curated first.
 */

export const IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp']

export function isImageFile(file: File): boolean {
  const name = file.name.toLowerCase()
  return IMAGE_EXTENSIONS.some((extension) => name.endsWith(extension))
}

/**
 * SKUs a file might be claiming, best guess first.
 *
 * The containing folder wins outright when there is one: a folder per SKU is
 * the natural way to collect photographs, and it is the only unambiguous
 * signal here. Filenames are not, because this catalogue contains part numbers
 * that are prefixes of other part numbers - `021-256-10` and `021-256-10-4`
 * are both real, different products. So `021-256-10-4.jpg` genuinely means
 * either "photo 4 of the first" or "a photo of the second", and nothing in the
 * name settles it.
 *
 * Failing a folder, suffixes are stripped one at a time and every prefix is
 * offered, longest first, so the caller can take the longest that is a real
 * product. That resolves `02411-u1-4` to `02411` (nothing longer exists) while
 * still reading `021-256-10-4` as itself. It is a guess, but it is the guess
 * the name most directly supports, and the resolved SKU is shown on screen so
 * a wrong one is visible rather than silent.
 *
 * Mirrors `expected_sku` in scripts/rigidhitch_score_real_photos.py, which has
 * the same folder-first rule. That one strips a single suffix because it can
 * check the index directly and its inputs are always foldered; this one cannot
 * assume either.
 */
export function candidateSkus(file: File): string[] {
  const relative = (file as File & { webkitRelativePath?: string }).webkitRelativePath ?? ''
  const segments = relative.split('/').filter(Boolean)
  const folder = segments.length > 1 ? segments[segments.length - 2] : ''
  const stem = file.name.replace(/\.[^.]+$/, '')

  const guesses: string[] = []
  const push = (value: string) => {
    const trimmed = value.trim().toUpperCase()
    if (trimmed && !guesses.includes(trimmed)) guesses.push(trimmed)
  }

  if (folder) push(folder)
  for (const token of stem.split(/[^A-Za-z0-9-]+/)) {
    if (!token) continue
    // Longest first, then one trailing "-U1" / "-4" group at a time. The loop
    // is bounded by the number of hyphens, and a part number is never reduced
    // past its first segment.
    let current = token.toUpperCase()
    push(current)
    while (/-(?:U\d+|\d+)$/.test(current)) {
      current = current.replace(/-(?:U\d+|\d+)$/, '')
      push(current)
    }
  }
  return guesses
}

/**
 * The SKU this file claims, if any of its guesses is a real product.
 *
 * Asking the catalogue is what separates "the search got this wrong" from
 * "this file never named a part" - without it the two are indistinguishable,
 * and an unnamed file would be counted as a miss. Results are cached because a
 * folder of one product's photographs asks the same question fifteen times.
 */
const skuCache = new Map<string, boolean>()

export async function resolveExpectedSku(file: File): Promise<string | null> {
  for (const guess of candidateSkus(file)) {
    const cached = skuCache.get(guess)
    if (cached === false) continue
    if (cached === true) return guess
    try {
      await getProduct(guess)
      skuCache.set(guess, true)
      return guess
    } catch {
      skuCache.set(guess, false)
    }
  }
  return null
}

export type BatchVerdict = 'top1' | 'top5' | 'miss' | 'unscored'

export function verdictFor(expectedSku: string | null, rankedSkus: string[]): BatchVerdict {
  if (!expectedSku) return 'unscored'
  if (rankedSkus[0] === expectedSku) return 'top1'
  return rankedSkus.includes(expectedSku) ? 'top5' : 'miss'
}

export interface BatchTotals {
  scored: number
  top1: number
  top5: number
  unscored: number
}

export function tally(verdicts: BatchVerdict[]): BatchTotals {
  const totals: BatchTotals = { scored: 0, top1: 0, top5: 0, unscored: 0 }
  for (const verdict of verdicts) {
    if (verdict === 'unscored') {
      totals.unscored += 1
      continue
    }
    totals.scored += 1
    if (verdict === 'top1') {
      totals.top1 += 1
      totals.top5 += 1
    } else if (verdict === 'top5') {
      totals.top5 += 1
    }
  }
  return totals
}
