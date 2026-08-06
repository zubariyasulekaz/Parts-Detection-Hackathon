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

function buildUrl(path: string, params?: QueryParams): string {
  const url = new URL(`${BASE_URL}${API_PREFIX}${path}`)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, String(value))
    }
  }
  return url.toString()
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
  let response: Response
  try {
    response = await fetch(buildUrl(path, params), { headers: { Accept: 'application/json' } })
  } catch {
    throw new ApiError('Could not reach the PartPilot backend. Confirm it is running and reachable.', 0)
  }
  return unwrap<T>(response)
}

export async function apiPostForm<T>(path: string, formData: FormData, params?: QueryParams): Promise<T> {
  let response: Response
  try {
    response = await fetch(buildUrl(path, params), { method: 'POST', body: formData })
  } catch {
    throw new ApiError('Could not reach the PartPilot backend. Confirm it is running and reachable.', 0)
  }
  return unwrap<T>(response)
}

export async function apiDelete<T>(path: string, params?: QueryParams): Promise<T> {
  let response: Response
  try {
    response = await fetch(buildUrl(path, params), {
      method: 'DELETE',
      headers: { Accept: 'application/json' },
    })
  } catch {
    throw new ApiError('Could not reach the PartPilot backend. Confirm it is running and reachable.', 0)
  }
  return unwrap<T>(response)
}
