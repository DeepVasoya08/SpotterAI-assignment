import { describe, expect, it } from 'vitest'

import { boundsOf, checkpointsCollection, riskGradient } from '@/features/map/mapData'
import { RISK_COLORS } from '@/lib/risk'
import { checkpoint, plannedRoute } from '@/test/fixtures'

describe('riskGradient', () => {
  it('changes colour midway between checkpoints of different risk', () => {
    const route = plannedRoute('r', {
      checkpoints: [
        checkpoint(0),
        checkpoint(50, 'severe'),
        checkpoint(100, 'severe'),
        checkpoint(200),
      ],
    })

    expect(riskGradient(route)).toEqual([
      'step',
      ['line-progress'],
      RISK_COLORS.low,
      0.125,
      RISK_COLORS.severe,
      0.75,
      RISK_COLORS.low,
    ])
  })

  it('uses a single valid stop for a route at one risk level', () => {
    const route = plannedRoute('r', {
      checkpoints: [checkpoint(0, 'high'), checkpoint(80, 'high')],
    })

    expect(riskGradient(route)).toEqual([
      'step',
      ['line-progress'],
      RISK_COLORS.high,
      1,
      RISK_COLORS.high,
    ])
  })
})

describe('checkpointsCollection', () => {
  it('creates a coloured point per checkpoint', () => {
    const route = plannedRoute('r', { checkpoints: [checkpoint(0), checkpoint(50, 'no_travel')] })

    const features = checkpointsCollection(route).features

    expect(features.map((feature) => feature.properties)).toEqual([
      { index: 0, level: 'low', color: RISK_COLORS.low },
      { index: 1, level: 'no_travel', color: RISK_COLORS.no_travel },
    ])
    expect(features[1]?.geometry.coordinates).toEqual([-99, 40])
  })
})

describe('boundsOf', () => {
  it('covers every route', () => {
    const north = plannedRoute('a', {
      geometry: [
        [-100, 45],
        [-90, 46],
      ],
    })
    const south = plannedRoute('b', {
      geometry: [
        [-105, 30],
        [-95, 31],
      ],
    })

    expect(boundsOf([north, south])).toEqual([-105, 30, -90, 46])
  })

  it('is null without routes', () => {
    expect(boundsOf([])).toBeNull()
  })
})
