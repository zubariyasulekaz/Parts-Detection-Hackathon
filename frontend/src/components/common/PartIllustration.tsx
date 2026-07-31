import { AirVent, Bolt, Cable, CircleDashed, Disc3, Droplet, Package, RadioTower, ShieldHalf, Wind, Zap } from 'lucide-react'
import type { ComponentType } from 'react'
import { ExhaustManifoldGlyph } from './ExhaustManifoldGlyph'
import { ShockAbsorberGlyph } from './ShockAbsorberGlyph'

type IconComponent = ComponentType<{ className?: string; strokeWidth?: number; 'aria-hidden'?: boolean }>

const CATEGORY_ICONS: Record<string, IconComponent> = {
  'Exhaust Manifold': ExhaustManifoldGlyph,
  'Brake Pads': Disc3,
  'Oil Filter': Droplet,
  'Air Filter': Wind,
  'Spark Plug': Zap,
  'Cabin Filter': AirVent,
  'Shock Absorbers': ShockAbsorberGlyph,
  Gaskets: CircleDashed,
  Hardware: Bolt,
  'Heat Shields': ShieldHalf,
  Sensors: RadioTower,
  Ignition: Cable,
}

interface PartIllustrationProps {
  category: string
  className?: string
}

/** Consistent placeholder "photo" tile for any product/category without real photography yet. */
export function PartIllustration({ category, className = '' }: PartIllustrationProps) {
  const Icon = CATEGORY_ICONS[category] ?? Package
  return (
    <div
      role="img"
      aria-label={`${category} placeholder illustration`}
      className={`bg-grid relative flex items-center justify-center overflow-hidden bg-linear-to-br from-surface-2 to-surface-3 ${className}`}
    >
      <Icon className="h-2/5 w-2/5 text-subtle" strokeWidth={1.25} aria-hidden />
    </div>
  )
}
