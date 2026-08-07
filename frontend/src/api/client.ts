/**
 * Thin fetch wrapper around the FastAPI backend's `StandardResponse[T]` /
 * `ErrorResponse` envelope (see `backend/schemas/response.py`). This is the
 * only module that should reference `VITE_API_BASE_URL` / `VITE_API_PREFIX`
 * directly — everything else goes through `partpilotApi.ts`.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '')
const API_PREFIX = import.meta.env.VITE_API_PREFIX.startsWith('/')
  ? import.meta.env.VITE_API_PREFIX
  : `/${import.meta.env.VITE_API_PREFIX}`

export class ApiError extends Error {
  readonly status: number
  readonly errorCode?: string

  constructor(message: string, status: number, errorCode?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.errorCode = errorCode
  }
}

interface Envelope<T> {
  success: boolean
  message: string
  data: T | null
}

interface ErrorBody {
  message?: string
  error_code?: string
}

type QueryParams = Record<string, string | number | boolean | undefined>

/** Most calls are catalog/history reads that should fail fast. */
const DEFAULT_TIMEOUT_MS = 15_000

function buildUrl(path: string, params?: QueryParams): string {
  const url = new URL(`${BASE_URL}${API_PREFIX}${path}`)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, String(value))
    }
  }
  return url.toString()
}

/**
 * `fetch` with a deadline. Without one, a hung backend leaves the UI on a
 * pulsing spinner forever — a timeout turns that into a retryable error.
 */
async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs: number): Promise<Response> {
  try {
    return await fetch(url, { ...init, signal: AbortSignal.timeout(timeoutMs) })
  } catch (error) {
    if (error instanceof DOMException && (error.name === 'TimeoutError' || error.name === 'AbortError')) {
      throw new ApiError(
        `The PartPilot backend did not respond within ${Math.round(timeoutMs / 1000)}s. It may still be starting up — try again.`,
        0,
      )
    }
    throw new ApiError('Could not reach the PartPilot backend. Confirm it is running and reachable.', 0)
  }
}

async function unwrap<T>(response: Response): Promise<T> {
  let body: unknown
  try {
    body = await response.json()
  } catch {
    throw new ApiError('The server returned an unreadable response.', response.status)
  }

  if (!response.ok) {
    const errorBody = body as ErrorBody
    throw new ApiError(
      errorBody?.message ?? `Request failed with status ${response.status}.`,
      response.status,
      errorBody?.error_code,
    )
  }

  const envelope = body as Envelope<T>
  if (!envelope.success || envelope.data === null || envelope.data === undefined) {
    throw new ApiError(envelope.message ?? 'The server returned an empty response.', response.status)
  }
  return envelope.data
}

export async function apiGet<T>(path: string, params?: QueryParams): Promise<T> {
  const response = await fetchWithTimeout(
    buildUrl(path, params),
    { headers: { Accept: 'application/json' } },
    DEFAULT_TIMEOUT_MS,
  )
  return unwrap<T>(response)
}

export async function apiPostForm<T>(
  path: string,
  formData: FormData,
  params?: QueryParams,
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const response = await fetchWithTimeout(buildUrl(path, params), { method: 'POST', body: formData }, timeoutMs)
  return unwrap<T>(response)
}

export async function apiPostJson<T>(path: string, body: unknown, params?: QueryParams): Promise<T> {
  const response = await fetchWithTimeout(
    buildUrl(path, params),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
    },
    DEFAULT_TIMEOUT_MS,
  )
  return unwrap<T>(response)
}

export async function apiDelete<T>(path: string, params?: QueryParams): Promise<T> {
  const response = await fetchWithTimeout(
    buildUrl(path, params),
    { method: 'DELETE', headers: { Accept: 'application/json' } },
    DEFAULT_TIMEOUT_MS,
  )
  return unwrap<T>(response)
}
