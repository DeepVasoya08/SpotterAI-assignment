import type {
  CorridorForecast,
  CorridorForecastRequest,
  Place,
  TripPlan,
  TripRequest,
} from '@/api/types'

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, 'Could not reach the server. Check your connection and try again.')
  }

  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response))
  }
  return (await response.json()) as T
}

/** Turns DRF error payloads ({detail} or {field: [messages]}) into one sentence. */
async function errorMessage(response: Response): Promise<string> {
  const fallback = `Request failed (${response.status}).`
  try {
    const body: unknown = await response.json()
    if (typeof body !== 'object' || body === null) return fallback
    if ('detail' in body && typeof body.detail === 'string') return body.detail
    const first = Object.values(body).flat()[0]
    return typeof first === 'string' ? first : fallback
  } catch {
    return fallback
  }
}

export async function searchPlaces(query: string, signal?: AbortSignal): Promise<Place[]> {
  const params = new URLSearchParams({ q: query })
  const body = await request<{ results: Place[] }>(`/api/places/?${params}`, {
    signal: signal ?? null,
  })
  return body.results
}

export function planTrip(trip: TripRequest): Promise<TripPlan> {
  return request<TripPlan>('/api/trips/plan/', {
    method: 'POST',
    body: JSON.stringify(trip),
  })
}

export function fetchCorridorForecast(
  corridor: CorridorForecastRequest,
  signal?: AbortSignal,
): Promise<CorridorForecast> {
  return request<CorridorForecast>('/api/trips/corridor-forecast/', {
    method: 'POST',
    body: JSON.stringify(corridor),
    signal: signal ?? null,
  })
}
