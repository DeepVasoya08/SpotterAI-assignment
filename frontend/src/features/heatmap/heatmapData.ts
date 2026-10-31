import type { ExpressionSpecification } from 'maplibre-gl'
import type { Feature, FeatureCollection, Polygon } from 'geojson'

import type { CorridorForecast, LatLon, PlannedRoute } from '@/api/types'
import { RISK_COLORS } from '@/lib/risk'

export const HEATMAP_MODES = ['risk', 'wind', 'rain', 'snow'] as const
export type HeatmapMode = (typeof HEATMAP_MODES)[number]

export const HEATMAP_MODE_LABELS: Record<HeatmapMode, string> = {
  risk: 'Risk',
  wind: 'Wind',
  rain: 'Rain',
  snow: 'Snow',
}

const PROPERTY_PREFIX: Record<HeatmapMode, string> = { risk: 'r', wind: 'w', rain: 'p', snow: 's' }

/**
 * Values at which each measure enters Moderate, High, Severe and No Travel. Every mode is
 * coloured through these bands, so a colour means the same thing on every layer. Rain
 * and snow No Travel starts just above the Severe ceiling, as in the risk rules.
 */
const BAND_STARTS: Record<HeatmapMode, [number, number, number, number]> = {
  risk: [1, 2, 3, 4],
  wind: [25, 35, 45, 55],
  rain: [0.1, 0.25, 0.5, 1.005],
  snow: [0.5, 1, 2, 3.005],
}

const BAND_COLORS = [
  RISK_COLORS.low,
  RISK_COLORS.moderate,
  RISK_COLORS.high,
  RISK_COLORS.severe,
  RISK_COLORS.no_travel,
] as const

// Calm cells stay faint so the corridor is visible without hiding the basemap.
const BAND_OPACITY = [0.12, 0.38, 0.45, 0.5, 0.55] as const

export function propertyKey(mode: HeatmapMode, hour: number): string {
  return `${PROPERTY_PREFIX[mode]}${hour}`
}

/**
 * One square per forecast cell carrying every hourly value, so moving the slider only
 * restyles the layer and never re-uploads data.
 */
export function corridorCollection(forecast: CorridorForecast): FeatureCollection<Polygon> {
  const half = forecast.step_degrees / 2
  const features: Feature<Polygon>[] = forecast.cells.map((cell) => {
    const properties: Record<string, number> = {}
    for (let hour = 0; hour < forecast.hours; hour += 1) {
      properties[propertyKey('risk', hour)] = cell.risk[hour] ?? 0
      properties[propertyKey('wind', hour)] = cell.wind_gust_mph[hour] ?? 0
      properties[propertyKey('rain', hour)] = cell.rain_in_per_hr[hour] ?? 0
      properties[propertyKey('snow', hour)] = cell.snow_in_per_hr[hour] ?? 0
    }
    const [west, east] = [cell.lon - half, cell.lon + half]
    const [south, north] = [cell.lat - half, cell.lat + half]
    return {
      type: 'Feature',
      properties,
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [west, south],
            [east, south],
            [east, north],
            [west, north],
            [west, south],
          ],
        ],
      },
    }
  })
  return { type: 'FeatureCollection', features }
}

function bandStep(
  mode: HeatmapMode,
  hour: number,
  outputs: readonly (string | number)[],
): ExpressionSpecification {
  const stops = BAND_STARTS[mode].flatMap((start, band) => [start, outputs[band + 1] ?? 0])
  return [
    'step',
    ['get', propertyKey(mode, hour)],
    outputs[0] ?? 0,
    ...stops,
  ] as ExpressionSpecification
}

export function cellColor(mode: HeatmapMode, hour: number): ExpressionSpecification {
  return bandStep(mode, hour, BAND_COLORS)
}

export function cellOpacity(mode: HeatmapMode, hour: number): ExpressionSpecification {
  return bandStep(mode, hour, BAND_OPACITY)
}

/** Where the truck is on ``route`` at ``time``, interpolated between checkpoint ETAs. */
export function positionAt(route: PlannedRoute, time: Date): LatLon | null {
  const target = time.getTime()
  const checkpoints = route.checkpoints
  const first = checkpoints[0]
  const last = checkpoints.at(-1)
  if (!first || !last) return null
  if (target <= Date.parse(first.eta)) return { lat: first.lat, lon: first.lon }
  if (target >= Date.parse(last.eta)) return { lat: last.lat, lon: last.lon }

  for (let index = 1; index < checkpoints.length; index += 1) {
    const previous = checkpoints[index - 1]
    const next = checkpoints[index]
    if (!previous || !next) continue
    const start = Date.parse(previous.eta)
    const end = Date.parse(next.eta)
    if (target <= end) {
      const fraction = end > start ? (target - start) / (end - start) : 0
      return {
        lat: previous.lat + (next.lat - previous.lat) * fraction,
        lon: previous.lon + (next.lon - previous.lon) * fraction,
      }
    }
  }
  return { lat: last.lat, lon: last.lon }
}
