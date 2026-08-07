import { ContactShadows, Environment, Lightformer } from '@react-three/drei'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { useEffect, useMemo, useRef } from 'react'
import type { Group } from 'three'

/**
 * Resting orientation: the rotor is tipped off head-on so both the friction
 * face and the machined edge are visible at once. Straight-on reads as a flat
 * circle - the whole point of spending a WebGL context here is the edge.
 */
const BASE_TILT_X = Math.PI / 2 - 0.52
const BASE_TILT_Z = 0.16

/**
 * The rotor does not spin at rest.
 *
 * A continuously rotating object sits in peripheral vision right beside the
 * page's only call to action, and motion captures attention involuntarily - so
 * a permanent spin competes with "upload a photo" on every second of every
 * visit, while the impression it buys is spent in the first two. What stays is
 * motion the visitor causes: a one-time entrance, then pointer parallax.
 *
 * Yaw offset the rotor settles from on first paint.
 */
const ENTRANCE_YAW = -0.85
/** Fraction of the remaining angle closed per frame while settling in. */
const ENTRANCE_EASE = 0.045
/** Below this, the entrance and the parallax are treated as finished. */
const SETTLE_EPSILON = 0.0008

/** Steel, cast iron, and the two brand lights, kept in sync with index.css. */
const COLORS = {
  disc: '#97a3b2',
  hat: '#6f7c8d',
  bore: '#161d2b',
  accent: '#2f80ed',
  accent2: '#2dd4bf',
} as const

/**
 * Normalised -1..1 pointer position, tracked on `window` rather than read from
 * fiber's `state.pointer`.
 *
 * The canvas sits behind the hero copy with `pointer-events: none` - it has to,
 * or it would eat clicks meant for the upload zone - and an element that
 * receives no pointer events also never updates fiber's pointer state. Watching
 * the window keeps the parallax alive without putting a hit-testing surface
 * over the page's primary call to action.
 */
function useWindowPointer(enabled: boolean) {
  const pointer = useRef({ x: 0, y: 0 })
  // The canvas renders on demand, so a pointer move has to explicitly ask for
  // the next frame - otherwise the parallax target changes and nothing repaints.
  const invalidate = useThree((state) => state.invalidate)

  useEffect(() => {
    if (!enabled) return
    const handleMove = (event: PointerEvent) => {
      pointer.current.x = (event.clientX / window.innerWidth) * 2 - 1
      // Flipped to match three's convention of +Y up against the DOM's +Y down.
      pointer.current.y = -((event.clientY / window.innerHeight) * 2 - 1)
      invalidate()
    }
    window.addEventListener('pointermove', handleMove, { passive: true })
    return () => window.removeEventListener('pointermove', handleMove)
  }, [enabled, invalidate])

  return pointer
}

interface RotorProps {
  /** Freeze the spin and the pointer parallax; keep the geometry and lighting. */
  still: boolean
}

function Rotor({ still }: RotorProps) {
  const spin = useRef<Group>(null)
  const tilt = useRef<Group>(null)
  const pointer = useWindowPointer(!still)
  const hasSettled = useRef(false)

  // Cross-drilled cooling holes, two concentric rings. The disc is a cylinder
  // on the Y axis, so its face lies in XZ and the holes only vary in X/Z.
  const drilledHoles = useMemo(() => {
    const positions: [number, number, number][] = []
    for (const [radius, count] of [
      [1.52, 16],
      [1.84, 22],
    ] as const) {
      for (let i = 0; i < count; i += 1) {
        const angle = (i / count) * Math.PI * 2
        positions.push([Math.cos(angle) * radius, 0, Math.sin(angle) * radius])
      }
    }
    return positions
  }, [])

  const lugHoles = useMemo(
    () =>
      Array.from({ length: 5 }, (_, i) => {
        const angle = (i / 5) * Math.PI * 2
        return [Math.cos(angle) * 0.6, 0.3, Math.sin(angle) * 0.6] as [number, number, number]
      }),
    [],
  )

  const slots = useMemo(() => Array.from({ length: 6 }, (_, i) => (i / 6) * Math.PI * 2), [])

  useFrame((state) => {
    const spinGroup = spin.current
    const tiltGroup = tilt.current
    if (!spinGroup || !tiltGroup) return

    if (still) {
      spinGroup.rotation.y = 0
      return
    }

    // On demand rendering: each frame has to earn the next one. When both the
    // entrance and the parallax have settled nothing calls invalidate, the loop
    // stops, and the GPU goes idle until the visitor moves the pointer again.
    let wantsAnotherFrame = false

    if (!hasSettled.current) {
      spinGroup.rotation.y += -spinGroup.rotation.y * ENTRANCE_EASE
      if (Math.abs(spinGroup.rotation.y) < SETTLE_EPSILON) {
        spinGroup.rotation.y = 0
        hasSettled.current = true
      } else {
        wantsAnotherFrame = true
      }
    }

    // Parallax toward the cursor, damped by hand: lerping the rotation rather
    // than assigning it means fast pointer travel across the hero glides
    // instead of snapping.
    const targetX = BASE_TILT_X + pointer.current.y * 0.2
    const targetZ = BASE_TILT_Z + pointer.current.x * 0.16
    tiltGroup.rotation.x += (targetX - tiltGroup.rotation.x) * 0.045
    tiltGroup.rotation.z += (targetZ - tiltGroup.rotation.z) * 0.045
    if (
      Math.abs(targetX - tiltGroup.rotation.x) > SETTLE_EPSILON ||
      Math.abs(targetZ - tiltGroup.rotation.z) > SETTLE_EPSILON
    ) {
      wantsAnotherFrame = true
    }

    if (wantsAnotherFrame) state.invalidate()
  })

  return (
    <group ref={tilt} rotation={[BASE_TILT_X, 0, BASE_TILT_Z]}>
      {/* Starts turned away and settles to zero once, so the reveal still lands
          on first paint without committing the page to permanent motion. */}
      <group ref={spin} rotation={[0, ENTRANCE_YAW, 0]}>
        {/* friction disc */}
        <mesh castShadow receiveShadow>
          <cylinderGeometry args={[2.1, 2.1, 0.22, 72]} />
          <meshStandardMaterial color={COLORS.disc} metalness={0.95} roughness={0.31} />
        </mesh>

        {/* machined shoulder where the friction ring steps down to the hat */}
        <mesh position={[0, 0.02, 0]}>
          <cylinderGeometry args={[1.28, 1.28, 0.26, 56]} />
          <meshStandardMaterial color={COLORS.hat} metalness={0.9} roughness={0.45} />
        </mesh>

        {/* mounting hat, proud of the disc face */}
        <mesh castShadow position={[0, 0.3, 0]}>
          <cylinderGeometry args={[0.86, 0.98, 0.5, 48]} />
          <meshStandardMaterial color={COLORS.hat} metalness={0.88} roughness={0.5} />
        </mesh>

        {/* centre bore - a dark cylinder standing in for a real boolean cut,
            which would need a CSG pass for a hole nobody sees the inside of */}
        <mesh position={[0, 0.32, 0]}>
          <cylinderGeometry args={[0.33, 0.33, 0.62, 32]} />
          <meshStandardMaterial color={COLORS.bore} metalness={0.4} roughness={0.85} />
        </mesh>

        {lugHoles.map((position, i) => (
          <mesh key={`lug-${i}`} position={position}>
            <cylinderGeometry args={[0.11, 0.11, 0.56, 20]} />
            <meshStandardMaterial color={COLORS.bore} metalness={0.4} roughness={0.85} />
          </mesh>
        ))}

        {drilledHoles.map((position, i) => (
          <mesh key={`hole-${i}`} position={position}>
            <cylinderGeometry args={[0.077, 0.077, 0.3, 14]} />
            <meshStandardMaterial color={COLORS.bore} metalness={0.3} roughness={0.9} />
          </mesh>
        ))}

        {slots.map((angle, i) => (
          <mesh key={`slot-${i}`} position={[0, 0.115, 0]} rotation={[0, angle, 0]}>
            <boxGeometry args={[0.055, 0.02, 0.62]} />
            <meshStandardMaterial color={COLORS.bore} metalness={0.3} roughness={0.9} />
          </mesh>
        ))}
      </group>

      {/* Scan ring: the product's identification motif, orbiting the part on a
          different axis from the spin so the two never lock into one motion. */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[2.42, 0.012, 8, 96]} />
        <meshStandardMaterial
          color={COLORS.accent2}
          emissive={COLORS.accent2}
          emissiveIntensity={2.2}
          toneMapped={false}
        />
      </mesh>
    </group>
  )
}

interface HeroPart3DProps {
  /** Honours the reader's reduced-motion preference: geometry stays, motion goes. */
  still?: boolean
  className?: string
}

/**
 * The landing hero's WebGL object - a cross-drilled brake rotor, built from
 * three.js primitives rather than a loaded `.glb`, so the repo carries no
 * binary model asset and the mesh recolours with the theme.
 *
 * Default-exported for `React.lazy`: three + fiber + drei are ~600 KB, and
 * every route that isn't the landing page should never pay for them. Load it
 * through `HeroPartStage`, which owns the lazy boundary and the fallbacks.
 *
 * Lighting is explicit lightformers inside a locally-generated environment
 * map - drei's named `Environment` presets fetch an HDRI from a CDN, which
 * would add a network dependency to a page that otherwise has none.
 */
export default function HeroPart3D({ still = false, className = '' }: HeroPart3DProps) {
  return (
    <Canvas
      className={className}
      // Capped at 2: past that the fragment cost on a 4K display buys nothing
      // visible on an object this size.
      dpr={[1, 2]}
      camera={{ position: [0, 0.4, 7.4], fov: 38 }}
      gl={{ antialias: true, alpha: true }}
      // Nothing moves unless the visitor makes it move, so a permanent 60fps
      // loop would spend the GPU redrawing an identical frame for as long as
      // the page is open. `demand` renders only when the entrance is still
      // settling or a pointer move has invalidated the last frame.
      frameloop="demand"
      // Purely decorative, and the page behind it carries the real content.
      aria-hidden="true"
    >
      <ambientLight intensity={0.35} />
      <directionalLight position={[4, 6, 5]} intensity={2.1} castShadow />
      <pointLight position={[-5, 2, 3]} intensity={38} distance={18} color={COLORS.accent} />
      <pointLight position={[5, -2, 2]} intensity={26} distance={16} color={COLORS.accent2} />

      <Rotor still={still} />

      {/* Bright strips for the metal to reflect - without these the steel has
          nothing to mirror and reads as flat grey plastic. */}
      <Environment resolution={256}>
        <Lightformer form="rect" intensity={3} position={[-4, 3, 4]} scale={[7, 4, 1]} color="#ffffff" />
        <Lightformer form="rect" intensity={2.4} position={[4, -1, 3]} scale={[6, 3, 1]} color={COLORS.accent} />
        <Lightformer form="circle" intensity={2} position={[0, 5, -3]} scale={5} color={COLORS.accent2} />
      </Environment>

      {/* `frames={1}` bakes the shadow once. Left at its default it re-renders
          the shadow map on every frame and keeps invalidating, which holds the
          whole canvas at full frame rate forever and defeats `frameloop="demand"`.
          The rotor only tilts a few degrees under the pointer, so a static
          contact shadow is indistinguishable from a live one. */}
      <ContactShadows frames={1} position={[0, -2.5, 0]} opacity={0.5} scale={12} blur={2.8} far={5} color="#000000" />
    </Canvas>
  )
}
