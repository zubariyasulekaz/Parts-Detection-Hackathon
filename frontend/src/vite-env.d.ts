/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "mock" serves canned data from src/mocks; "live" calls the FastAPI backend. */
  readonly VITE_API_MODE: 'mock' | 'live'
  /** Origin of the FastAPI backend, e.g. http://localhost:8000 (no trailing slash, no /api/v1). */
  readonly VITE_API_BASE_URL: string
  /** Versioned API prefix appended to VITE_API_BASE_URL, matches Settings.API_PREFIX in the backend. */
  readonly VITE_API_PREFIX: string
  /** How many candidate matches to request from the /predict endpoint. */
  readonly VITE_PREDICTION_TOP_K: string
  /** "false" skips Brain 4, so /predict never waits on the LLM. Anything else requests an explanation. */
  readonly VITE_PREDICTION_EXPLAIN: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
