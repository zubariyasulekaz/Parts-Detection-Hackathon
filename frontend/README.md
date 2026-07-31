# PartPilot Frontend

AI-Powered Visual Parts Identification — the web client for the PartPilot
FastAPI backend in `../partpilot/backend`.

Vite + React 19 + TypeScript + React Router + Tailwind CSS v4. No Redux —
state is a small `useReducer`-backed React Context
(`src/context/IdentificationContext.tsx`) that tracks the uploaded image,
identification result, and confirmation/selection state across the
upload → processing → results → product-details journey.

## Getting started

```bash
npm install
npm run dev       # starts the Vite dev server (defaults to http://localhost:5173)
```

Other scripts:

```bash
npm run build      # tsc -b && vite build -> dist/
npm run preview    # serve the production build locally
npm run lint       # oxlint
```

## Mock mode vs. live API mode

Configuration lives in `.env` (copy `.env.example` to start):

```bash
VITE_API_MODE=mock              # "mock" | "live"
VITE_API_BASE_URL=http://localhost:8000
VITE_API_PREFIX=/api/v1
VITE_PREDICTION_TOP_K=5
```

- **`mock`** (default) — every page runs entirely against canned data in
  `src/mocks/`, via `src/services/identificationService.ts` and
  `src/services/catalogService.ts`. No backend required.
- **`live`** — the same two services call the real FastAPI backend
  through `src/api/partpilotApi.ts` (`POST /predict`, `GET /products`,
  `GET /products/{sku}`, `GET /products/{sku}/recommendations`), then
  normalize the response through `src/adapters/` before it reaches any
  component.

Switching modes never touches a component or page — only the service
layer branches on `VITE_API_MODE`.

## Project layout

```
src/
  api/            fetch wrapper (client.ts) + typed backend calls (partpilotApi.ts)
  adapters/       backend DTO -> frontend domain-type mapping
  services/       identificationService, catalogService — the mock/live switch lives here
  mocks/          canned catalog + identification scenarios (mock mode only)
  types/          Product, IdentificationResult, API DTOs, etc.
  context/        IdentificationProvider — cross-page journey state
  components/     grouped by feature (landing, processing, results, product, architecture, common, layout)
  pages/          one component per route
```

See the root project instructions / conversation history for the full
rationale; this file covers day-to-day usage only.
