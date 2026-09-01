/**
 * Measured retrieval performance, surfaced where a reader can actually see it.
 *
 * Every figure here is **held out**: the query photograph is excluded from its
 * own product's centroid, so a photo is never matched against itself. That
 * distinction is the whole point of the panel. The same pipeline scored with
 * indexed photos returns numbers in the nineties, and those numbers mean
 * nothing - they measure whether a file equals itself. They must never appear
 * on this page.
 *
 * Regenerate with:
 *   python scripts/rigidhitch_eval_index.py --query-split test
 *   python scripts/rigidhitch_score_real_photos.py --photos <folder>
 */

const MEASURED_AT = '7,510 products - 13,701 photographs - held-out queries'

const HEADLINE = [
  { label: 'Category', value: '89.7%', note: 'right kind of part, ranked first' },
  { label: 'Top-5 SKU', value: '70.2%', note: 'exact product in the top five' },
  { label: 'Top-1 SKU', value: '36.1%', note: 'exact product ranked first' },
] as const

interface TrainingRow {
  model: string
  detail: string
  top1: number
  top5: number
  emphasis?: boolean
}

/**
 * What the fine-tune actually bought. Without this row-over-row comparison the
 * headline reads as "an image search scores 70%", which is unremarkable; the
 * point is that the same architecture scores 49.9% until it is trained on this
 * catalogue.
 */
const TRAINING: TrainingRow[] = [
  { model: 'DINOv2, off the shelf', detail: 'facebook/dinov2-base, frozen', top1: 23.3, top5: 49.9 },
  { model: 'Fine-tuned, 12 epochs', detail: 'ArcFace margin loss', top1: 33.4, top5: 66.5 },
  { model: 'Fine-tuned, 24 epochs', detail: 'shipped', top1: 36.1, top5: 70.2, emphasis: true },
]

interface LimitRow {
  headline: string
  value: string
  detail: string
}

/**
 * The limits, stated rather than buried. A reader who finds these themselves
 * stops trusting the numbers above; a reader handed them tends to trust both.
 */
const LIMITS: LimitRow[] = [
  {
    headline: 'Products a photo can find',
    value: '7,510 of 10,813',
    detail:
      '3,303 products carry no photograph of their own - their catalogue image is a placeholder '
      + 'shared across the range, one of which served 367 different products. They are excluded '
      + 'from the index rather than answered wrongly.',
  },
  {
    headline: 'Real phone photographs',
    value: '61.5% top-1 - 79.5% top-5',
    detail:
      '39 photographs taken by hand, of products whose index entries held only studio shots. '
      + 'Lower than the catalogue figures, and the honest number for a customer standing in a yard '
      + 'with a phone. Adding real photographs of a product lifts it sharply.',
  },
  {
    headline: 'Where it is weakest',
    value: 'Wiring connectors, 50.7%',
    detail:
      'Categories whose products are the same shape in every size - connectors, truck accessories '
      + 'at 65.1%. What separates those SKUs is a number, not a silhouette, and no camera reads it.',
  },
]

export function PerformancePanel() {
  return (
    <section aria-labelledby="measured-performance">
      <div className="text-center">
        <p className="text-xs font-bold tracking-[0.2em] text-accent-hover uppercase">Measured</p>
        <h2 id="measured-performance" className="mt-3 text-xl font-bold text-foreground">
          Retrieval accuracy
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-muted">
          Scored exactly as the running search scores it, on photographs held out of the index. A
          photo is never matched against itself - which is the difference between a number that
          means something and one that does not.
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

      <p className="mx-auto mt-4 max-w-2xl text-center text-xs leading-relaxed text-subtle">
        Category accuracy is the number that matters for a parts counter: a photograph reliably
        finds the right kind of part and a shortlist to confirm from. Naming the exact SKU from a
        photograph alone is not something this catalogue supports - two ball mounts that differ by
        a load rating are the same picture.
      </p>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.35fr_1fr]">
        <div className="shadow-depth overflow-hidden rounded-xl border border-border bg-surface">
          <div className="border-b border-border px-5 py-3.5">
            <h3 className="text-sm font-bold text-foreground">What training on this catalogue bought</h3>
            <p className="mt-0.5 text-xs text-muted">
              Same architecture throughout. The difference is 24 epochs on RigidHitch&apos;s own products.
            </p>
          </div>
          {/* Wide content scrolls inside its own container so the page body never does. */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-subtle">
                <tr className="border-b border-border">
                  <th scope="col" className="px-5 py-2.5 font-semibold">Model</th>
                  <th scope="col" className="px-3 py-2.5 font-semibold">Detail</th>
                  <th scope="col" className="px-3 py-2.5 text-right font-semibold">Top-1</th>
                  <th scope="col" className="px-5 py-2.5 text-right font-semibold">Top-5</th>
                </tr>
              </thead>
              <tbody>
                {TRAINING.map((row) => (
                  <tr
                    key={row.model}
                    className={`border-b border-border/60 last:border-0 ${row.emphasis ? 'bg-accent/6' : ''}`}
                  >
                    <td className="px-5 py-2.5 font-medium text-foreground">{row.model}</td>
                    <td className="px-3 py-2.5 text-muted">{row.detail}</td>
                    <td className="px-3 py-2.5 text-right font-mono text-muted">{row.top1.toFixed(1)}%</td>
                    <td
                      className={`px-5 py-2.5 text-right font-mono font-semibold ${
                        row.emphasis ? 'text-accent-soft' : 'text-foreground'
                      }`}
                    >
                      {row.top5.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="border-t border-border px-5 py-3 text-xs leading-relaxed text-subtle">
            A further +17.9 points of top-5 comes from PCA whitening the stored vectors - the single
            largest gain that required no retraining.
          </p>
        </div>

        <div className="shadow-depth rounded-xl border border-border bg-surface p-5">
          <h3 className="text-sm font-bold text-foreground">What it cannot do</h3>
          <p className="mt-1.5 text-xs leading-relaxed text-muted">
            Stated here rather than discovered later. Each of these was measured, and each is the
            reason a number above is not higher.
          </p>
          <dl className="mt-4 space-y-3">
            {LIMITS.map((row) => (
              <div key={row.headline} className="rounded-lg border border-border-strong bg-surface-2 p-3.5">
                <dt className="flex items-baseline justify-between gap-3">
                  <span className="text-xs font-bold text-foreground">{row.headline}</span>
                  <span className="shrink-0 font-mono text-xs text-warning-soft">{row.value}</span>
                </dt>
                <dd className="mt-1.5 text-xs leading-relaxed text-muted">{row.detail}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </section>
  )
}
