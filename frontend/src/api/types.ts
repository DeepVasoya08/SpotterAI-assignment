// Mirrors the JSON returned by the Django API (see backend/trips/presenters.py).

export const RISK_LEVELS = ['low', 'moderate', 'high', 'severe', 'no_travel'] as const
export type RiskLevel = (typeof RISK_LEVELS)[number]

export type Hazard = 'wind' | 'rain' | 'snow'

export const SAMPLING_INTERVALS_MILES = [10, 25, 50] as const
export type SamplingInterval = (typeof SAMPLING_INTERVALS_MILES)[number]

export type RankingCriterion =
  | 'only_route'
  | 'avoids_no_travel'
  | 'fewer_no_travel_miles'
  | 'fewer_severe_miles'
  | 'fewer_high_miles'
  | 'lower_average_risk'
  | 'shorter_travel_time'
  | 'tied'

export interface LatLon {
  lat: number
  lon: number
}

export interface Place extends LatLon {
  id: string
  label: string
}

export interface CheckpointWeather {
  wind_speed_mph: number
  wind_gust_mph: number
  rain_in_per_hr: number
  snow_in_per_hr: number
}

export interface CheckpointRisk {
  level: RiskLevel
  hazard_levels: Record<Hazard, RiskLevel>
  causes: Hazard[]
  load_adjusted: boolean
}

export interface Checkpoint extends LatLon {
  distance_miles: number
  represented_miles: number
  eta: string
  weather: CheckpointWeather
  risk: CheckpointRisk
}

export interface RouteSummary {
  miles_by_level: Record<RiskLevel, number>
  average_risk: number
  max_level: RiskLevel
}

export interface PlannedRoute {
  id: string
  distance_miles: number
  duration_s: number
  arrival_time: string
  summary: RouteSummary
  /** GeoJSON order: [lon, lat]. */
  geometry: [number, number][]
  checkpoints: Checkpoint[]
}

export interface Recommendation {
  route_id: string
  decided_by: RankingCriterion
  all_routes_blocked: boolean
  ranking: string[]
}

export interface TripPlan {
  departure_time: string
  load_weight_lb: number
  sampling_interval_miles: SamplingInterval
  recommendation: Recommendation
  routes: PlannedRoute[]
}

export interface TripRequest {
  origin: LatLon
  destination: LatLon
  departure_time: string
  load_weight_lb: number
  sampling_interval_miles: SamplingInterval
}
