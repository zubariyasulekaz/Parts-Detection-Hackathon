import { AmbientBackground } from '@/components/layout/AmbientBackground'
import { PageContainer } from '@/components/layout/PageContainer'
import { ArchitectureDiagram } from '@/components/architecture/ArchitectureDiagram'

interface StackItem {
  name: string
  kind: 'AI Model' | 'Vector Search' | 'Database' | 'Backend Framework'
  description: string
}

const STACK_ITEMS: StackItem[] = [
  {
    name: 'EfficientNet',
    kind: 'AI Model',
    description: 'Fine-tuned image classifier used by Brain 1 to predict part category.',
  },
  {
    name: 'DINOv2',
    kind: 'AI Model',
    description:
      'Brain 2’s default embedding model. Self-supervised on images alone, so it matches on “is this the same object” rather than on what the part is called.',
  },
  {
    name: 'OpenCLIP',
    kind: 'AI Model',
    description:
      'The alternative Brain 2 backend, kept for the categories that benchmarked better on it than on DINOv2 — air filters, wheel hubs, and shock absorbers.',
  },
  {
    name: 'Qwen (Transformers)',
    kind: 'AI Model',
    description: 'Brain 4’s LLM — generates the explanation and clarifying questions, when requested.',
  },
  {
    name: 'FAISS',
    kind: 'Vector Search',
    description: 'Searches category-scoped embedding indexes for the nearest catalog matches.',
  },
  {
    name: 'PostgreSQL',
    kind: 'Database',
    description: 'Stores catalog metadata, compatibility, and product relationships for Brain 3.',
  },
  {
    name: 'FastAPI',
    kind: 'Backend Framework',
    description: 'Serves the HTTP API that orchestrates the end-to-end pipeline.',
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
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-foreground">How PartPilot identifies a part</h1>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          A single uploaded photograph moves through four specialized stages — classification, visual similarity
          search, catalog intelligence, and an optional LLM explanation — before a ranked set of candidate products
          reaches the frontend.
        </p>
      </div>

      <div className="mt-14">
        <ArchitectureDiagram />
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
                className={`w-fit rounded-full border px-2.5 py-1 text-[10px] font-semibold tracking-wide uppercase ${KIND_BADGE_CLASS[item.kind]}`}
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
          The architecture is designed to support customer-specific catalogs with tens of thousands of products
          while keeping product metadata separate from the visual search index.
        </p>
      </div>
      </PageContainer>
    </div>
  )
}
