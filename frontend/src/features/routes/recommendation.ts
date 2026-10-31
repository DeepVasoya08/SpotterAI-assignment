import type { PlannedRoute, RiskLevel, TripPlan } from '@/api/types'
import { formatDuration, formatMiles } from '@/lib/format'

export interface RecommendationText {
  headline: string
  reason: string
  /** True when the driver should not set off with the current plan. */
  warning: boolean
}

/**
 * Explains the recommendation in the driver's terms, comparing the chosen route with
 * the runner-up on the criterion that separated them.
 */
export function describeRecommendation(
  plan: TripPlan,
  labelOf: (routeId: string) => string,
): RecommendationText {
  const { recommendation } = plan
  const best = findRoute(plan, recommendation.route_id)
  const runnerUpId = recommendation.ranking[1]
  const runnerUp = runnerUpId ? findRoute(plan, runnerUpId) : undefined
  const bestLabel = labelOf(best.id)
  const headline = `Take ${bestLabel}`

  if (recommendation.all_routes_blocked) {
    return {
      headline: 'Every route crosses No Travel conditions',
      reason: `${bestLabel} has the fewest No Travel miles (${miles(best, 'no_travel')}). Consider a later departure.`,
      warning: true,
    }
  }
  if (!runnerUp) {
    return { headline, reason: `${bestLabel} is the only truck route available.`, warning: false }
  }

  const otherLabel = labelOf(runnerUp.id)
  const reasons: Record<typeof recommendation.decided_by, string> = {
    only_route: `${bestLabel} is the only truck route available.`,
    avoids_no_travel: `${otherLabel} crosses No Travel conditions; ${bestLabel} avoids them.`,
    fewer_no_travel_miles: `${bestLabel} has the fewest No Travel miles.`,
    fewer_severe_miles: `${miles(best, 'severe')} of Severe weather versus ${miles(runnerUp, 'severe')} on ${otherLabel}.`,
    fewer_high_miles: `Equal Severe exposure, and ${miles(best, 'high')} of High risk versus ${miles(runnerUp, 'high')} on ${otherLabel}.`,
    lower_average_risk: `Equal Severe and High exposure, with lower overall risk than ${otherLabel}.`,
    shorter_travel_time: `As safe as ${otherLabel} and ${formatDuration(runnerUp.duration_s - best.duration_s)} faster.`,
    tied: `${bestLabel} and ${otherLabel} are equally safe and fast.`,
  }
  return { headline, reason: reasons[recommendation.decided_by], warning: false }
}

function findRoute(plan: TripPlan, routeId: string): PlannedRoute {
  const route = plan.routes.find((candidate) => candidate.id === routeId)
  if (!route) throw new Error(`Route ${routeId} is missing from the plan.`)
  return route
}

function miles(route: PlannedRoute, level: RiskLevel): string {
  return formatMiles(route.summary.miles_by_level[level])
}
