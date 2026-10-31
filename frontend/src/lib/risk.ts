import type { Hazard, RiskLevel } from '@/api/types'

export const RISK_LABELS: Record<RiskLevel, string> = {
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  severe: 'Severe',
  no_travel: 'No Travel',
}

export const RISK_COLORS: Record<RiskLevel, string> = {
  low: '#16a34a',
  moderate: '#eab308',
  high: '#f97316',
  severe: '#dc2626',
  no_travel: '#581c87',
}

export const HAZARD_LABELS: Record<Hazard, string> = {
  wind: 'Wind',
  rain: 'Rain',
  snow: 'Snow',
}
