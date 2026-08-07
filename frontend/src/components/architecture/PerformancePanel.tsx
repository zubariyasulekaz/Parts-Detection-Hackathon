/**
 * Measured retrieval performance, surfaced where a reader can actually see it.
 *
 * These figures already existed - in `settings.py` comments and in the stdout of
 * `scripts/analyze_index_vectors.py` - which meant nobody outside the codebase
 * ever saw them. From the outside, "DINOv2 by default with three OpenCLIP
 * exceptions" is indistinguishable from hardcoding exceptions until something
 * worked. The numbers are what separate the two.
 *
 * Regenerate with `python scripts/analyze_index_vectors.py` and update here;
 * the script reads the vectors already stored in the built FAISS indexes, so it
 * measures the running system rather than a re-embedded approximation.
 */

const MEASURED_AT = '56 products - 10 categories - 240 queries'

const HEADLINE = [
  { label: 'Top-1', value: '85.0%', note: 'correct SKU ranked first' },
  { label: 'Top-3', value: '96.7%', note: 'correct SKU in the top three' },
  { label: 'MRR', value: '0.911', note: '1.0 = always first' },
] as const

interface CategoryRow {
  category: string
  backend: 'dinov2' | 'openclip'
  skus: number
  queries: number
  top1: number
}

/** Ordered worst-first: the weak categories are the informative ones. */
const CATEGORIES: CategoryRow[] = [
  { category: 'Exhaust Manifold', backend: 'dinov2', skus: 8, queries: 24, top1: 70.8 },
  { category: 'Wheel Hub Assembly', backend: 'openclip', skus: 4, queries: 21, top1: 76.2 },
  { category: 'Brake Pads', backend: 'dinov2', skus: 6, queries: 31, top1: 77.4 },
  { category: 'Throttle Body', backend: 'dinov2', skus: 5, queries: 29, top1: 82.8 },
  { category: 'Suspension Bushing', backend: 'dinov2', skus: 8, queries: 24, top1: 83.3 },
  { category: 'Oil Filter', backend: 'dinov2', skus: 3, queries: 20, top1: 85.0 },
  { category: 'Air Filter', backend: 'openclip', skus: 5, queries: 22, top1: 90.9 },
  { category: 'Fuel Injector', backend: 'dinov2', skus: 5, queries: 29, top1: 93.1 },
  { category: 'Shock Absorber', backend: 'openclip', skus: 8, queries: 24, top1: 95.8 },
  { category: 'Power Steering Pump', backend: 'dinov2', skus: 4, queries: 16, top1: 100.0 },
]

interface RefusalRow {
  backend: string
  threshold: string
  rejected: string
  caught: string
}

const REFUSAL: RefusalRow[] = [
  { backend: 'DINOv2', threshold: '0.48', rejected: '1.2%', caught: '93.2%' },
  { backend: 'OpenCLIP', threshold: '0.86', rejected: '1.5%', caught: '60.4%' },
]

const BACKEND_CLASS: Record<CategoryRow['backend'], string> = {
  dinov2: 'border-accent/40 bg-accent/12 text-accent-soft',
  openclip: 'border-accent-2/40 bg-accent-2/10 text-accent-2',
}

export function PerformancePanel() {
  return (
    <section aria-labelledby="measured-performance">
      <div className="text-center">
        <p className="text-xs font-bold tracking-[0.2em] text-accent-hover uppercase">Measured</p>
        <h2 id="measured-performance" className="mt-3 text-xl font-bold text-foreground">
          Retrieval accuracy
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-muted">
          Leave-one-out over every catalog image, scored exactly as the running search scores it. The query image is
          excluded from its own product&apos;s centroid, so a photo is never matched against itself.
        </p>
        <p className="mt-2 font-mono text-xs text-subtle">{MEASURED_AT}</p>
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        {HEADLINE.map((metric) => (
          <div key={metric.label} className="shadow-depth rounded-xl border border-border-strong bg-surface p-5 text-center">
            <p className="text-xs font-bold tracking-[0.15em] text-subtle uppercase">{metric.label}</p>
            <p className="text-gradient-accent mt-2 font-mono text-3xl font-bold">{metric.value}</p>
            <p className="mt-1.5 text-xs text-muted">{metric.note}</p>
          </div>
        ))}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.35fr_1fr]">
        <div className="shadow-depth overflow-hidden rounded-xl border border-border bg-surface">
          <div className="border-b border-border px-5 py-3.5">
            <h3 className="text-sm font-bold text-foreground">Per category</h3>
            <p className="mt-0.5 text-xs text-muted">
              Weakest first. Exhaust manifolds and wheel hubs are where the catalog is hardest to tell apart.
            </p>
          </div>
          {/* Wide content scrolls inside its own container so the page body never does. */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-subtle">
                <tr className="border-b border-border">
                  <th scope="col" className="px-5 py-2.5 font-semibold">Category</th>
                  <th scope="col" className="px-3 py-2.5 font-semibold">Model</th>
                  <th scope="col" className="px-3 py-2.5 text-right font-semibold">SKUs</th>
                  <th scope="col" className="px-3 py-2.5 text-right font-semibold">Queries</th>
                  <th scope="col" className="px-5 py-2.5 text-right font-semibold">Top-1</th>
                </tr>
              </thead>
              <tbody>
                {CATEGORIES.map((row) => (
                  <tr key={row.category} className="border-b border-border/60 last:border-0">
                    <td className="px-5 py-2.5 font-medium text-foreground">{row.category}</td>
                    <td className="px-3 py-2.5">
                      <span className={`rounded-full border px-2 py-0.5 font-mono text-[0.65rem] ${BACKEND_CLASS[row.backend]}`}>
                        {row.backend}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-muted">{row.skus}</td>
                    <td className="px-3 py-2.5 text-right font-mono text-muted">{row.queries}</td>
                    <td className="px-5 py-2.5 text-right font-mono font-semibold text-foreground">
                      {row.top1.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="shadow-depth rounded-xl border border-border bg-surface p-5">
          <h3 className="text-sm font-bold text-foreground">The cost of refusing</h3>
          <p className="mt-1.5 text-xs leading-relaxed text-muted">
            No-match thresholds are calibrated against measured correct-match and impostor score distributions, not
            chosen by feel. The trade is explicit: rejecting a small share of correct matches in exchange for catching
            most wrong ones.
          </p>
          <dl className="mt-4 space-y-3">
            {REFUSAL.map((row) => (
              <div key={row.backend} className="rounded-lg border border-border-strong bg-surface-2 p-3.5">
                <dt className="flex items-baseline justify-between">
                  <span className="text-xs font-bold text-foreground">{row.backend}</span>
                  <span className="font-mono text-xs text-subtle">threshold {row.threshold}</span>
                </dt>
                <dd className="mt-2 flex gap-5">
                  <span className="text-xs text-muted">
                    <span className="block font-mono text-sm font-semibold text-warning-soft">{row.rejected}</span>
                    correct rejected
                  </span>
                  <span className="text-xs text-muted">
                    <span className="block font-mono text-sm font-semibold text-success-soft">{row.caught}</span>
                    impostors caught
                  </span>
                </dd>
              </div>
            ))}
          </dl>
          <p className="mt-3.5 text-xs leading-relaxed text-subtle">
            OpenCLIP&apos;s correct and impostor scores genuinely overlap more, which is why it catches fewer. It is
            kept only for the three categories where it ranks far better than DINOv2.
          </p>
        </div>
      </div>
    </section>
  )
}
