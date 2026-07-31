/**
 * Hand-authored SVG markup, not user input — safe to inject verbatim.
 * Shared between the landing-page hero card (rendered live in the DOM)
 * and services/sampleImage.ts (rasterized to a PNG File for "Try Sample
 * Image", so the sample submission is a real image the backend can decode).
 *
 * Named generically (not after the specific part) so swapping the
 * featured hero part later doesn't leave a stale identifier behind.
 */
export const HERO_PART_SVG_MARKUP = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" preserveAspectRatio="xMidYMid slice" role="img" aria-label="Shock absorber illustration">
  <defs>
    <radialGradient id="bg" cx="50%" cy="38%" r="75%">
      <stop offset="0%" stop-color="#1e2833" />
      <stop offset="100%" stop-color="#0b0f14" />
    </radialGradient>
    <radialGradient id="glow" cx="50%" cy="50%" r="52%">
      <stop offset="0%" stop-color="#2f80ed" stop-opacity="0.38" />
      <stop offset="100%" stop-color="#2f80ed" stop-opacity="0" />
    </radialGradient>
    <linearGradient id="steel" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#e2e8f0" />
      <stop offset="22%" stop-color="#aab6c2" />
      <stop offset="55%" stop-color="#6b7684" />
      <stop offset="100%" stop-color="#232b34" />
    </linearGradient>
    <linearGradient id="steelDark" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8a95a3" />
      <stop offset="100%" stop-color="#1a2027" />
    </linearGradient>
  </defs>

  <rect width="400" height="400" fill="url(#bg)" />
  <circle cx="200" cy="200" r="168" fill="url(#glow)" />

  <g stroke="#2f80ed" stroke-width="2" stroke-linecap="round" opacity="0.55">
    <path d="M24,52 L24,24 L52,24" fill="none" />
    <path d="M348,24 L376,24 L376,52" fill="none" />
    <path d="M24,348 L24,376 L52,376" fill="none" />
    <path d="M376,348 L376,376 L348,376" fill="none" />
  </g>

  <!-- Kept within y=60-340 on purpose: the landing card crops this artwork
       to a 4:3 window, so content spanning the full 400-tall viewBox would
       lose its top/bottom (this bit us with an earlier spark-plug design). -->
  <g stroke="#0e1318" stroke-width="1.5">
    <rect x="164" y="60" width="72" height="26" rx="7" fill="url(#steel)" />
    <circle cx="178" cy="73" r="4" fill="#12171d" />
    <circle cx="200" cy="73" r="4" fill="#12171d" />
    <circle cx="222" cy="73" r="4" fill="#12171d" />

    <rect x="192" y="86" width="16" height="26" fill="url(#steelDark)" />
    <rect x="182" y="104" width="36" height="224" rx="10" fill="url(#steelDark)" />

    <g fill="none" stroke="url(#steel)" stroke-width="7">
      <ellipse cx="200" cy="132" rx="46" ry="12" />
      <ellipse cx="200" cy="156" rx="46" ry="12" />
      <ellipse cx="200" cy="180" rx="46" ry="12" />
      <ellipse cx="200" cy="204" rx="46" ry="12" />
      <ellipse cx="200" cy="228" rx="46" ry="12" />
      <ellipse cx="200" cy="252" rx="46" ry="12" />
    </g>

    <rect x="176" y="308" width="48" height="32" rx="8" fill="url(#steel)" />
    <circle cx="200" cy="324" r="8" fill="#12171d" />
  </g>

  <g stroke="#ffffff" stroke-width="1.5" opacity="0.3" stroke-linecap="round">
    <path d="M190,108 L190,300" fill="none" />
  </g>
</svg>
`.trim()
