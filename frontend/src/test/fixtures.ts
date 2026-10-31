import type { Checkpoint, PlannedRoute, RiskLevel, TripPlan } from '@/api/types'

export function checkpoint(distance: number, level: RiskLevel = 'low'): Checkpoint {
  return {
    distance_miles: distance,
    represented_miles: 10,
    lat: 40,
    lon: -100 + distance / 50,
    eta: '2026-11-01T15:00:00Z',
    weather: { wind_speed_mph: 10, wind_gust_mph: 15, rain_in_per_hr: 0, snow_in_per_hr: 0 },
    risk: {
      level,
      hazard_levels: { wind: level, rain: 'low', snow: 'low' },
      causes: level === 'low' ? [] : ['wind'],
      load_adjusted: false,
    },
  }
}

export function plannedRoute(
  id: string,
  overrides: Partial<PlannedRoute> & { miles?: Partial<Record<RiskLevel, number>> } = {},
): PlannedRoute {
  const { miles = {}, ...rest } = overrides
  return {
    id,
    distance_miles: 100,
    duration_s: 6000,
    arrival_time: '2026-11-01T16:40:00Z',
    summary: {
      miles_by_level: { low: 100, moderate: 0, high: 0, severe: 0, no_travel: 0, ...miles },
      average_risk: 0,
      max_level: 'low',
    },
    geometry: [
      [-100, 40],
      [-99, 40.5],
      [-98, 40],
    ],
    checkpoints: [checkpoint(0), checkpoint(50), checkpoint(100)],
    ...rest,
  }
}

export function tripPlan(
  routes: PlannedRoute[],
  overrides: Partial<TripPlan['recommendation']> = {},
): TripPlan {
  return {
    departure_time: '2026-11-01T15:00:00Z',
    load_weight_lb: 40000,
    sampling_interval_miles: 25,
    routes,
    recommendation: {
      route_id: routes[0]?.id ?? '',
      decided_by: 'only_route',
      all_routes_blocked: false,
      ranking: routes.map((route) => route.id),
      ...overrides,
    },
  }
}
