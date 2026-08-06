import {
  ArrowDown,
  Barcode,
  Camera,
  Cpu,
  Database,
  Network,
  PackageSearch,
  Search,
  SlidersHorizontal,
  Sparkles,
  Tag,
} from 'lucide-react'
import type { ComponentType } from 'react'
import { ArchitectureNode } from './ArchitectureNode'

interface NodeDefinition {
  icon: ComponentType<{ className?: string }>
  title: string
  description: string
  emphasis?: boolean
}

const NODES: NodeDefinition[] = [
  { icon: Camera, title: 'User Image', description: 'The uploaded part photograph enters the pipeline.' },
  {
    icon: SlidersHorizontal,
    title: 'Image Preprocessing',
    description: 'Validates the upload and normalizes the image for the classifier.',
  },
  {
    icon: Cpu,
    title: 'Brain 1: Fine-tuned EfficientNet Classifier',
    description: 'Predicts the part category from the processed image.',
    emphasis: true,
  },
  { icon: Tag, title: 'Predicted Part Category', description: 'e.g. Exhaust Manifold, Brake Pads, Oil Filter.' },
  {
    icon: Network,
    title: 'Brain 2: DINOv2 / OpenCLIP Image Embedding',
    description:
      'Generates a visual embedding of the image for similarity search. DINOv2 by default, with OpenCLIP kept for the categories it scores better on.',
    emphasis: true,
  },
  {
    icon: Search,
    title: 'FAISS Similarity Search',
    description: 'Searches the category-scoped vector index for the closest matches.',
  },
  { icon: Barcode, title: 'Top-K Catalog SKUs', description: 'Ranked candidate SKUs with similarity scores.' },
  {
    icon: Database,
    title: 'Brain 3: PostgreSQL Catalog Intelligence',
    description: 'Resolves each SKU to full catalog metadata and relationships.',
    emphasis: true,
  },
  {
    icon: Sparkles,
    title: 'Brain 4: Qwen LLM Reasoning (optional)',
    description: 'Generates a short natural-language explanation, and clarifying questions when the match is ambiguous.',
    emphasis: true,
  },
  {
    icon: PackageSearch,
    title: 'Product Details, Compatibility, Replacements, Alternatives, Accessories',
    description: 'The complete response — plus the AI explanation, when requested — returned to the frontend.',
  },
]

export function ArchitectureDiagram() {
  return (
    <div className="flex flex-col items-center">
      {NODES.map((node, index) => (
        <div key={node.title} className="flex w-full flex-col items-center">
          <div className="animate-pop-in w-full max-w-lg" style={{ animationDelay: `${index * 90}ms` }}>
            <ArchitectureNode {...node} />
          </div>
          {index < NODES.length - 1 && (
            <div className="flex flex-col items-center py-1">
              <div className="h-6 w-px bg-linear-to-b from-accent/50 to-accent/10" aria-hidden="true" />
              <ArrowDown className="h-4 w-4 text-accent/50" aria-hidden="true" />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
