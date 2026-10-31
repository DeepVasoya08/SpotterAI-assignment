import type { ExpressionSpecification, LngLatBoundsLike } from 'maplibre-gl'
import type { Feature, FeatureCollection, LineString, Point } from 'geojson'

import type { PlannedRoute, RiskLevel } from '@/api/types'
import { RISK_COLORS } from '@/lib/risk'

export interface RouteProperties {
  id: string
}

export interface CheckpointProperties {
  index: number
  level: RiskLevel
  color: string
}

export function routeFeature(route: PlannedRoute): Feature<LineString, RouteProperties> {
  return {
    type: 'Feature',
    properties: { id: route.id },
    geometry: { type: 'LineString', coordinates: route.geometry },
  }
}

export function routesCollection(
  routes: PlannedRoute[],
): FeatureCollection<LineString, RouteProperties> {
  return { type: 'FeatureCollection', features: routes.map(routeFeature) }
}

export function checkpointsCollection(
  route: PlannedRoute,
): FeatureCollection<Point, CheckpointProperties> {
  return {
    type: 'FeatureCollection',
    features: route.checkpoints.map((checkpoint, index) => ({
      type: 'Feature',
      properties: {
        index,
        level: checkpoint.risk.level,
        color: RISK_COLORS[checkpoint.risk.level],
      },
      geometry: { type: 'Point', coordinates: [checkpoint.lon, checkpoint.lat] },
    })),
  }
}

/**
 * A `line-gradient` that colours the route by checkpoint risk. Each checkpoint covers the
 * road halfway to its neighbours, matching how the backend counts risk miles, so the
 * colour changes at the midpoint between checkpoints.
 */
export function riskGradient(route: PlannedRoute): ExpressionSpecification {
  const [first, ...rest] = route.checkpoints
  if (!first) return solidGradient(RISK_COLORS.low)
  const total = route.checkpoints.at(-1)?.distance_miles ?? 0

  // Checkpoint distances strictly increase, so the stops do too.
  const stops: (string | number)[] = []
  let previous = first
  for (const checkpoint of rest) {
    if (checkpoint.risk.level !== previous.risk.level) {
      stops.push((previous.distance_miles + checkpoint.distance_miles) / 2 / total)
      stops.push(RISK_COLORS[checkpoint.risk.level])
    }
    previous = checkpoint
  }

  const startColor = RISK_COLORS[first.risk.level]
  if (stops.length === 0) return solidGradient(startColor)
  return ['step', ['line-progress'], startColor, ...stops] as ExpressionSpecification
}

/** A `step` expression needs at least one stop, even for a single colour. */
function solidGradient(color: string): ExpressionSpecification {
  return ['step', ['line-progress'], color, 1, color]
}

export function boundsOf(routes: PlannedRoute[]): LngLatBoundsLike | null {
  let minLon = Infinity
  let minLat = Infinity
  let maxLon = -Infinity
  let maxLat = -Infinity
  for (const route of routes) {
    for (const [lon, lat] of route.geometry) {
      minLon = Math.min(minLon, lon)
      minLat = Math.min(minLat, lat)
      maxLon = Math.max(maxLon, lon)
      maxLat = Math.max(maxLat, lat)
    }
  }
  return Number.isFinite(minLon) ? [minLon, minLat, maxLon, maxLat] : null
}
