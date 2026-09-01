import { AmbientBackground } from '@/components/layout/AmbientBackground'
import { PageContainer } from '@/components/layout/PageContainer'
import { ArchitectureDiagram } from '@/components/architecture/ArchitectureDiagram'
import { PerformancePanel } from '@/components/architecture/PerformancePanel'

interface StackItem {
  name: string
  kind: 'AI Model' | 'Vector Search' | 'Database' | 'Backend Framework'
  description: string
}

const STACK_ITEMS: StackItem[] = [
  {
    name: 'DINOv2, fine-tuned',
    kind: 'AI Model',
    description:
      'Self-supervised on images alone, so it matches on “is this the same object” rather than on what the part is called - then retrained on RigidHitch’s own catalogue, which is what takes top-5 from 49.9% to 70.2%.',
  },
  {
    name: 'ArcFace margin loss',
    kind: 'AI Model',
    description:
      'The training objective. Every product folder is a label the catalogue already provides, so the model learns to separate look-alike SKUs without anyone hand-labelling a thing.',
  },
  {
    name: 'rembg / U²-Net',
    kind: 'AI Model',
    description:
      'Segments the part out of a customer’s background before it is compared against catalogue photographs taken on white.',
  },
  {
    name: 'PCA whitening',
    kind: 'Vector Search',
    description:
      'Rebalances the embedding so dimensions the catalogue barely varies on stop dominating. Worth +17.9 points of top-5, and it travels with the index rather than living in code.',
  },
  {
    name: 'FAISS',
    kind: 'Vector Search',
    description: 'Exact cosine search over 13,701 catalogue photographs, scored per product rather than per photo.',
  },
  {
    name: 'PostgreSQL',
    kind: 'Database',
    description: 'Holds the 10,813-product catalogue - names, brands, part numbers, specifications and image paths.',
  },
  {
    name: 'FastAPI',
    kind: 'Backend Framework',
    description: 'Serves the API. One endpoint does the identification; the rest read the catalogue.',
  },
]

const KIND_BADGE_CLASS: Record<StackItem['kind'], string> = {
  'AI Model': 'border-accent/30 bg-accent/10 text-accent-soft',
  'Vector Search': 'border-border-strong bg-surface-2 text-muted',
  Database: 'border-border-strong bg-surface-2 text-muted',
  'Backend Framework': 'border-border-strong bg-surface-2 text-muted',
}

export function ArchitecturePage() {
  return (
    <div className="relative overflow-hidden">
      <AmbientBackground className="opacity-60" />
      <PageContainer className="relative py-14">
      <div className="mx-auto max-w-2xl text-center">
        <span className="text-xs font-bold tracking-[0.2em] text-accent-hover uppercase">AI Architecture</span>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-foreground">How a photograph finds a part</h1>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          One photograph, cut from its background, turned into 768 numbers by a model trained on RigidHitch&apos;s
          own catalogue, and compared against every product photograph in it - returning a shortlist with its
          confidence stated rather than a single answer asserted.
        </p>
      </div>

      <div className="mt-14">
        <ArchitectureDiagram />
      </div>

      {/* Straight after the diagram: the pipeline claim, then the evidence for
          it, before the reader moves on to which libraries were used. */}
      <div className="mt-20">
        <PerformancePanel />
      </div>

      <div className="mt-16">
        <h2 className="text-center text-xl font-bold text-foreground">Open-Source AI Stack</h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {STACK_ITEMS.map((item, index) => (
            <div
              key={item.name}
              style={{ animationDelay: `${index * 70}ms` }}
              className="shadow-card animate-pop-in flex flex-col gap-2 rounded-xl border border-border bg-surface p-4"
            >
              <span
                className={`w-fit rounded-full border px-2.5 py-1 text-xs font-semibold tracking-wide uppercase ${KIND_BADGE_CLASS[item.kind]}`}
              >
                {item.kind}
              </span>
              <p className="text-sm font-bold text-foreground">{item.name}</p>
              <p className="text-xs leading-relaxed text-muted">{item.description}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="shadow-card mx-auto mt-14 max-w-3xl rounded-xl border border-border bg-surface p-6 text-center">
        <p className="text-sm leading-relaxed text-muted">
          Product metadata is kept separate from the visual index, so the catalogue can change - new products,
          new photographs, corrected specifications - without retraining anything. Adding real photographs of a
          product is the one change that measurably improves it, and it takes minutes.
        </p>
      </div>
      </PageContainer>
    </div>
  )
}
