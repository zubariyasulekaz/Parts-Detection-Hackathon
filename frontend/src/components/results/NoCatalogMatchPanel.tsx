import { PackageX } from 'lucide-react'
import { StatusBadge } from '@/components/common/StatusBadge'
import { NO_CATALOG_MATCH_THRESHOLD } from '@/services/identificationService'
import { formatPercent } from '@/utils/format'
import type { CategoryPrediction, IdentificationCandidate } from '@/types/identification'

interface NoCatalogMatchPanelProps {
  category: CategoryPrediction
  /** Rank-1 result, i.e. the closest thing Brain 2 found - absent when the search returned nothing at all. */
  closestCandidate: IdentificationCandidate | null
  /** The server-side threshold the verdict was made against; falls back to the mock-mode constant. */
  threshold?: number | null
  /**
   * How the verdict was reached, which changes what is honest to say.
   *
   * `'score'` - nothing scored high enough, so the image probably is not a part.
   * `'user'`  - the customer said none of the results is their part. The scores
   *             here are perfectly normal, so the threshold sentence would be
   *             false; a 34% top match is typical of a real phone photograph of
   *             a part we *do* stock. The system had no way to know: measured on
   *             200 queries, no signal read off a photograph separates a stocked
   *             product from its nearest unstocked lookalike.
   */
  reason?: 'score' | 'user'
  onNewSearch: () => void
}

/**
 * Shown in place of the best-match summary when Brain 3 has nothing worth
 * resolving: the nearest catalog entry scored below the no-match threshold.
 *
 * The category prediction is still reported - Brain 1 answered a different
 * question and its answer stands - but the SKU is deliberately not presented as
 * a match, because recommending the wrong part is the expensive failure here.
 */
/**
 * Below this classifier confidence, a no-match result reports no category at
 * all. When neither model stood behind the image, naming a category is just
 * the least-wrong of ten options - for an out-of-catalog photo it reads as
 * "we think your living room is a suspension bushing".
 */
const CATEGORY_TRUST_THRESHOLD = 0.75

export function NoCatalogMatchPanel({
  category,
  closestCandidate,
  threshold,
  reason = 'score',
  onNewSearch,
}: NoCatalogMatchPanelProps) {
  const effectiveThreshold = threshold ?? NO_CATALOG_MATCH_THRESHOLD
  const categoryTrusted = category.confidence >= CATEGORY_TRUST_THRESHOLD
  const saidByUser = reason === 'user'
  return (
    <div className="shadow-card flex h-full flex-col gap-5 rounded-xl border border-warning/40 bg-surface p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="heading-eyebrow text-sm font-bold tracking-wide text-muted uppercase">Catalog Match</h2>
        <StatusBadge variant="warning">No catalog match</StatusBadge>
      </div>

      <div className="flex items-start gap-4">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-warning/40 bg-warning-muted/30 text-warning">
          <PackageX className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <p className="text-base font-semibold text-foreground">
            {saidByUser
              ? "We don't appear to stock this part"
              : categoryTrusted
                ? 'This part is not available in our catalog'
                : "We couldn't recognize a catalog part in this image"}
          </p>
          <p className="mt-1.5 text-sm text-muted">
            {saidByUser ? (
              <>
                Thanks - that's the one thing a photograph can't tell us. Parts from different manufacturers are
                often the same shape, so we can only narrow it down to what it looks like; you're the one who can
                read the brand off the part. Give our team a call with that name and they'll confirm whether we
                carry it.
              </>
            ) : closestCandidate ? (
              <>
                The closest entry we stock matches this photo at only{' '}
                <span className="font-mono font-semibold text-foreground">
                  {formatPercent(closestCandidate.similarity)}
                </span>{' '}
                visual similarity, which is under the {formatPercent(effectiveThreshold)} we require before calling
                something a match. Rather than recommend a part that probably isn't yours, we're flagging it.
              </>
            ) : (
              <>
                The visual search returned no catalog entries for this part, so there is nothing to match against.
              </>
            )}
          </p>
        </div>
      </div>

      <dl className="grid grid-cols-1 gap-4 rounded-lg border border-border-strong bg-surface-2 p-4 sm:grid-cols-2">
        <div>
          <dt className="text-xs font-semibold tracking-wide text-muted uppercase">Category Signal</dt>
          {categoryTrusted ? (
            <dd className="mt-1 text-sm font-semibold text-foreground">
              {category.name}{' '}
              <span className="font-mono text-xs font-normal text-subtle">
                (unconfirmed · {formatPercent(category.confidence)})
              </span>
            </dd>
          ) : (
            <dd className="mt-1 text-sm text-muted">
              Not recognized: no category claim at {formatPercent(category.confidence)} classifier confidence
            </dd>
          )}
        </div>
        <div>
          <dt className="text-xs font-semibold tracking-wide text-muted uppercase">Closest Catalog Entry</dt>
          <dd className="mt-1 font-mono text-sm text-muted">
            {closestCandidate ? `${closestCandidate.sku} · ${formatPercent(closestCandidate.similarity)}` : '-'}
          </dd>
        </div>
      </dl>

      <p className="text-xs text-subtle">
        A clearer, straight-on photo against a plain background often lifts the score enough to find a match. If it
        still comes back empty, we likely don't stock this part.
      </p>

      <div className="mt-auto pt-2">
        <button
          type="button"
          onClick={onNewSearch}
          className="rounded-lg border border-border-strong px-6 py-2.5 text-sm font-semibold text-foreground transition-colors hover:border-accent/50"
        >
          Try Another Photo
        </button>
      </div>
    </div>
  )
}
