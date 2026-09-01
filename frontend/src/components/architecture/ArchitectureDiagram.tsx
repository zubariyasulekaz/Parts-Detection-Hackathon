import {
  Barcode,
  Camera,
  Cpu,
  Database,
  Network,
  PackageSearch,
  Search,
  SlidersHorizontal,
  Tag,
} from 'lucide-react'
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ComponentType } from 'react'
import { useScrollProgress } from '@/hooks/useScrollProgress'
import { ArchitectureNode, type NodeKind } from './ArchitectureNode'

interface NodeDefinition {
  icon: ComponentType<{ className?: string }>
  title: string
  description: string
  kind: NodeKind
  emphasis?: boolean
}

const NODES: NodeDefinition[] = [
  {
    icon: Camera,
    title: 'Customer Photograph',
    description: 'A phone photo of a part someone is holding, or a screenshot of one they found.',
    kind: 'Input',
  },
  {
    icon: SlidersHorizontal,
    title: 'Background Removal',
    description:
      'The part is cut from whatever is behind it and placed on white, because that is how the catalogue photographs it. A workbench left in the frame becomes part of the fingerprint.',
    kind: 'Processing',
  },
  {
    icon: Cpu,
    title: 'Fine-tuned DINOv2',
    description:
      'A vision transformer retrained for 24 epochs on RigidHitch’s own 10,813 products, using an angular-margin loss that pulls photographs of one SKU together and pushes look-alikes apart.',
    kind: 'AI Model',
    emphasis: true,
  },
  {
    icon: Network,
    title: '768-dimension Embedding',
    description:
      'The photograph as a list of numbers. Averaged with its mirror image, then PCA-whitened so the dimensions the catalogue barely varies on stop dominating the comparison.',
    kind: 'Signal',
  },
  {
    icon: Search,
    title: 'FAISS Vector Search',
    description:
      '13,701 catalogue photographs across 7,510 products, compared by cosine similarity. One flat index, not one per category - half these products belong to more than one.',
    kind: 'Vector Search',
    emphasis: true,
  },
  {
    icon: Barcode,
    title: 'Ranked Shortlist',
    description:
      'The five closest products, each with its score. The gap between first and second is the confidence: wide means one clear answer, bunched means the system is guessing and says so.',
    kind: 'Signal',
  },
  {
    icon: Database,
    title: 'PostgreSQL Catalogue',
    description: 'Resolves each SKU to its name, brand, part number, specifications and photographs.',
    kind: 'Database',
    emphasis: true,
  },
  {
    icon: Tag,
    title: 'Guided Questions',
    description:
      'Asked only about what a photograph genuinely cannot show - drop height, ball diameter, load capacity - and only when the shortlist is too close to separate.',
    kind: 'Processing',
  },
  {
    icon: PackageSearch,
    title: 'Shortlist, with its limits stated',
    description:
      'The candidates, their scores, and a warning where one is owed: a load rating no camera can read, a match too weak to trust, or nothing in the catalogue that fits.',
    kind: 'Response',
  },
]

/** x of the single-column rail, in the gutter the container reserves with `pl-9`. */
const RAIL_X = 18
/** Cards alternate sides only once there is room for two columns. */
const WIDE_QUERY = '(min-width: 1024px)'

interface Point {
  x: number
  y: number
}

/**
 * How far the control points are pulled along the vertical gap. At 0.5 the
 * handles meet in the middle and the curve corners noticeably at each anchor;
 * past 0.5 they cross, which flattens the ends and throws the horizontal travel
 * into the middle of the span - a continuously flowing serpentine rather than a
 * chain of separate S-bends.
 */
const BEND = 0.62

/**
 * Smooth curve through the anchor points. Control points are pulled vertically
 * rather than toward the next point, which is what turns the alternating
 * left/right anchors into flowing bends instead of diagonal zig-zags.
 */
function buildPath(points: Point[]): string {
  if (points.length === 0) return ''
  let d = `M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`
  for (let i = 1; i < points.length; i += 1) {
    const previous = points[i - 1]
    const current = points[i]
    const bend = (current.y - previous.y) * BEND
    d +=
      ` C ${previous.x.toFixed(2)} ${(previous.y + bend).toFixed(2)},` +
      ` ${current.x.toFixed(2)} ${(current.y - bend).toFixed(2)},` +
      ` ${current.x.toFixed(2)} ${current.y.toFixed(2)}`
  }
  return d
}

/**
 * The pipeline as a scroll-driven journey: one connecting path that draws itself
 * as the reader scrolls, a pulse travelling along it, and each stage lighting up
 * as the pulse arrives.
 *
 * The path is *measured*, not hand-authored. Card heights change with text
 * wrapping and breakpoint, so a hardcoded `d` (or a CSS `offset-path`, whose
 * coordinates don't scale with a responsive container) would drift away from the
 * cards. Reading the real anchor positions and rebuilding the curve keeps the
 * line attached to the cards at every width.
 */
export function ArchitectureDiagram() {
  const cardRefs = useRef<(HTMLDivElement | null)[]>([])
  const progressPathRef = useRef<SVGPathElement>(null)
  const probePathRef = useRef<SVGPathElement>(null)
  const travelerRef = useRef<HTMLSpanElement>(null)
  /** Normalized 0..1 position of each stage along the path. */
  const stationsRef = useRef<number[]>([])

  const [path, setPath] = useState({ d: '', length: 0 })
  const [activeCount, setActiveCount] = useState(0)

  // Lets the rAF callback read the current path without being re-created on
  // every measurement, which would tear down and re-attach the scroll listener.
  const pathRef = useRef(path)
  pathRef.current = path

  const progressRef = useRef(0)

  const handleProgress = useCallback((progress: number) => {
    progressRef.current = progress
    const { length } = pathRef.current
    if (length > 0) {
      const line = progressPathRef.current
      if (line) line.style.strokeDashoffset = `${length * (1 - progress)}`

      const traveler = travelerRef.current
      const geometry = progressPathRef.current
      if (traveler && geometry) {
        const distance = length * progress
        const point = geometry.getPointAtLength(distance)
        // Look a good way ahead for the tangent. A 2px sample was numerically
        // noisy through the tight bends and made the comet's tail twitch; 14px
        // averages over enough curve to stay steady.
        const ahead = geometry.getPointAtLength(Math.min(distance + 14, length))
        const angle = (Math.atan2(ahead.y - point.y, ahead.x - point.x) * 180) / Math.PI
        traveler.style.transform = `translate(${point.x}px, ${point.y}px) translate(-50%, -50%) rotate(${angle}deg)`
        traveler.style.opacity = progress > 0.004 ? '1' : '0'
      }
    }

    let reached = 0
    for (const station of stationsRef.current) {
      // Tolerance: the first station sits at exactly 0 and should read as lit
      // the moment the section is on screen, not one pixel of scroll later.
      if (progress >= station - 0.001) reached += 1
    }
    setActiveCount(reached)
  }, [])

  // Slightly heavier than the default so the pulse reads as having mass, but
  // not so heavy that it visibly trails behind a fast fling scroll.
  const containerRef = useScrollProgress<HTMLDivElement>(handleProgress, { smoothing: 0.11 })

  const measure = useCallback(() => {
    const container = containerRef.current
    const probe = probePathRef.current
    if (!container || !probe) return

    const containerRect = container.getBoundingClientRect()
    const wide = window.matchMedia(WIDE_QUERY).matches

    const points: Point[] = []
    for (const [index, card] of cardRefs.current.entries()) {
      if (!card) continue
      const rect = card.getBoundingClientRect()
      const y = rect.top - containerRect.top + rect.height / 2
      // Single column: everything hangs off one rail. Two columns: the path
      // terminates on whichever edge the card's anchor dot sits on.
      const x = !wide ? RAIL_X : index % 2 === 0 ? rect.right - containerRect.left : rect.left - containerRect.left
      points.push({ x, y })
    }
    if (points.length < 2) return

    // Cumulative length at each stage, measured by growing the probe path one
    // node at a time. `getTotalLength` is exact for beziers, where sampling
    // would only approximate.
    const stations: number[] = []
    for (let i = 0; i < points.length; i += 1) {
      probe.setAttribute('d', buildPath(points.slice(0, i + 1)))
      stations.push(probe.getTotalLength())
    }
    const total = stations[stations.length - 1]
    stationsRef.current = total > 0 ? stations.map((value) => value / total) : stations.map(() => 0)

    const d = buildPath(points)
    setPath((current) => (current.d === d ? current : { d, length: total }))
  }, [containerRef])

  // Re-apply the current scroll position whenever the geometry changes. Without
  // this the path renders at its initial `strokeDashoffset` (= full length, so
  // nothing drawn) until the reader's *first scroll event* - a visitor landing
  // mid-page, or any resize, would see an undrawn path and unlit stages that
  // don't match where they actually are.
  useEffect(() => {
    handleProgress(progressRef.current)
  }, [handleProgress, path])

  useLayoutEffect(() => {
    measure()
    const container = containerRef.current
    if (!container) return
    // Card activation only changes transforms and colours, never layout, so
    // this observer can't feed itself.
    const observer = new ResizeObserver(measure)
    observer.observe(container)
    window.addEventListener('resize', measure)
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', measure)
    }
  }, [measure, containerRef])

  return (
    <div ref={containerRef} className="relative pl-9 lg:pl-0">
      <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full overflow-visible">
        <defs>
          {/* Both ends stay bright. The first version opened on `--color-accent`
              (#2f80ed), which is close enough to the page's navy that the
              freshly-drawn head of the path was invisible until it reached the
              cyan end - the draw-on effect only started reading a third of the
              way down. */}
          <linearGradient id="pipeline-flow" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-accent-soft)" />
            <stop offset="50%" stopColor="var(--color-accent-2)" />
            <stop offset="100%" stopColor="var(--color-accent-soft)" />
          </linearGradient>
        </defs>

        {/* Dormant track: shows the whole route up front, so the reader can see
            how far the story runs before committing to the scroll. */}
        <path
          d={path.d}
          fill="none"
          stroke="var(--color-border-strong)"
          strokeWidth={2}
          strokeLinecap="round"
          strokeDasharray="3 8"
        />
        <path
          ref={progressPathRef}
          d={path.d}
          fill="none"
          stroke="url(#pipeline-flow)"
          strokeWidth={3}
          strokeLinecap="round"
          style={{
            strokeDasharray: path.length,
            strokeDashoffset: path.length,
            filter: 'drop-shadow(0 0 9px rgba(45, 212, 191, 0.55))',
          }}
        />
        {/* Measuring instrument only - never painted. */}
        <path ref={probePathRef} fill="none" stroke="none" />
      </svg>

      {/* Card width leaves a ~14% channel between the columns. Narrower and the
          serpentine flattens into a straight line; wider and the cards get too
          cramped for the longer stage titles. */}
      <ol className="relative flex flex-col gap-7 lg:gap-9">
        {NODES.map((node, index) => (
          <li key={node.title} className={index % 2 === 0 ? 'lg:w-[43%]' : 'lg:ml-auto lg:w-[43%]'}>
            <div
              ref={(element) => {
                cardRefs.current[index] = element
              }}
            >
              <ArchitectureNode
                {...node}
                step={index + 1}
                side={index % 2 === 0 ? 'left' : 'right'}
                active={index < activeCount}
              />
            </div>
          </li>
        ))}
      </ol>

      {/* The pulse itself: a bright head with a tail that trails backwards along
          the local tangent (the wrapper is rotated, so -x is always "behind"). */}
      <span
        ref={travelerRef}
        aria-hidden="true"
        className="pointer-events-none absolute top-0 left-0 h-3 w-3 opacity-0 transition-opacity duration-500 will-change-transform"
      >
        <span className="absolute top-1/2 right-1/2 h-0.75 w-20 -translate-y-1/2 rounded-full bg-linear-to-l from-accent-2 to-transparent" />
        <span className="absolute inset-0 rounded-full bg-accent-2 shadow-[0_0_22px_7px_rgba(45,212,191,0.5)]" />
      </span>
    </div>
  )
}
