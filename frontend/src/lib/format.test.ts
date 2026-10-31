import { describe, expect, it } from 'vitest'

import { formatDuration, formatMiles, routeLabel, toDateTimeLocalValue } from '@/lib/format'

describe('formatDuration', () => {
  it.each([
    [45 * 60, '45 min'],
    [3600, '1 h'],
    [14 * 3600 + 38 * 60, '14 h 38 min'],
    [59.6 * 60, '1 h'],
  ])('formats %d seconds as %s', (seconds, expected) => {
    expect(formatDuration(seconds)).toBe(expected)
  })
})

describe('formatMiles', () => {
  it('rounds and groups thousands', () => {
    expect(formatMiles(1316.4)).toBe(`${(1316).toLocaleString()} mi`)
  })
})

describe('routeLabel', () => {
  it('letters routes from A', () => {
    expect([0, 1, 2].map(routeLabel)).toEqual(['Route A', 'Route B', 'Route C'])
  })
})

describe('toDateTimeLocalValue', () => {
  it('formats a local date for datetime-local inputs', () => {
    expect(toDateTimeLocalValue(new Date(2026, 0, 5, 7, 3))).toBe('2026-01-05T07:03')
  })
})
