import { describe, expect, it } from 'vitest'

import { describeRecommendation } from '@/features/routes/recommendation'
import { plannedRoute, tripPlan } from '@/test/fixtures'

const labelOf = (id: string) => `Route ${id.toUpperCase()}`

describe('describeRecommendation', () => {
  it('compares severe miles with the runner-up', () => {
    const plan = tripPlan(
      [plannedRoute('b', { miles: { severe: 0 } }), plannedRoute('a', { miles: { severe: 40 } })],
      { decided_by: 'fewer_severe_miles' },
    )

    expect(describeRecommendation(plan, labelOf)).toEqual({
      headline: 'Take Route B',
      reason: '0 mi of Severe weather versus 40 mi on Route A.',
      warning: false,
    })
  })

  it('states the time saved when risk is equal', () => {
    const plan = tripPlan(
      [plannedRoute('a', { duration_s: 3600 }), plannedRoute('b', { duration_s: 3600 + 45 * 60 })],
      { decided_by: 'shorter_travel_time' },
    )

    expect(describeRecommendation(plan, labelOf).reason).toBe(
      'As safe as Route B and 45 min faster.',
    )
  })

  it('warns when every route is blocked', () => {
    const plan = tripPlan([plannedRoute('a', { miles: { no_travel: 12 } }), plannedRoute('b')], {
      decided_by: 'fewer_no_travel_miles',
      all_routes_blocked: true,
    })

    const text = describeRecommendation(plan, labelOf)

    expect(text.warning).toBe(true)
    expect(text.headline).toBe('Every route crosses No Travel conditions')
    expect(text.reason).toContain('12 mi')
  })

  it('handles a single route', () => {
    const plan = tripPlan([plannedRoute('a')])

    expect(describeRecommendation(plan, labelOf).reason).toBe(
      'Route A is the only truck route available.',
    )
  })
})
