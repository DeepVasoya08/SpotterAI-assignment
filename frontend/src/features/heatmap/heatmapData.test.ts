import { describe, expect, it } from 'vitest'

import type { CorridorForecast } from '@/api/types'
import {
  cellColor,
  corridorCollection,
  positionAt,
  propertyKey,
} from '@/features/heatmap/heatmapData'
import { RISK_COLORS } from '@/lib/risk'
import { checkpoint, plannedRoute } from '@/test/fixtures'

const forecast: CorridorForecast = {
  start_time: '2026-11-01T15:00:00Z',
  step_degrees: 0.5,
  hours: 2,
  cells: [
    {
      lat: 40,
      lon: -100,
      risk: [0, 3],
      wind_gust_mph: [12, 48],
      rain_in_per_hr: [0, 0.3],
      snow_in_per_hr: [0, 0],
    },
  ],
}

describe('corridorCollection', () => {
  it('draws each cell as a square of the grid step', () => {
    const [feature] = corridorCollection(forecast).features

    expect(feature?.geometry.coordinates[0]).toEqual([
      [-100.25, 39.75],
      [-99.75, 39.75],
      [-99.75, 40.25],
      [-100.25, 40.25],
      [-100.25, 39.75],
    ])
  })

  it('carries every hourly value for every layer', () => {
    const [feature] = corridorCollection(forecast).features

    expect(feature?.properties).toEqual({
      r0: 0,
      r1: 3,
      w0: 12,
      w1: 48,
      p0: 0,
      p1: 0.3,
      s0: 0,
      s1: 0,
    })
  })
})

describe('cellColor', () => {
  it('colours wind with the risk thresholds', () => {
    expect(cellColor('wind', 7)).toEqual([
      'step',
      ['get', propertyKey('wind', 7)],
      RISK_COLORS.low,
      25,
      RISK_COLORS.moderate,
      35,
      RISK_COLORS.high,
      45,
      RISK_COLORS.severe,
      55,
      RISK_COLORS.no_travel,
    ])
  })
})

describe('positionAt', () => {
  const route = plannedRoute('r', {
    checkpoints: [
      { ...checkpoint(0), lat: 40, lon: -100, eta: '2026-11-01T15:00:00Z' },
      { ...checkpoint(60), lat: 41, lon: -99, eta: '2026-11-01T16:00:00Z' },
    ],
  })

  it('interpolates between checkpoint arrival times', () => {
    expect(positionAt(route, new Date('2026-11-01T15:30:00Z'))).toEqual({ lat: 40.5, lon: -99.5 })
  })

  it('stays at the origin before departure and the destination after arrival', () => {
    expect(positionAt(route, new Date('2026-11-01T14:00:00Z'))).toEqual({ lat: 40, lon: -100 })
    expect(positionAt(route, new Date('2026-11-02T00:00:00Z'))).toEqual({ lat: 41, lon: -99 })
  })
})
