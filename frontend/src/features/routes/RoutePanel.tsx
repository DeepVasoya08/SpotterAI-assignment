import { AlertTriangle, ShieldCheck } from 'lucide-react'
import { memo } from 'react'

import type { TripPlan } from '@/api/types'
import { cx } from '@/lib/cx'
import { describeRecommendation } from '@/features/routes/recommendation'
import { RouteCard } from '@/features/routes/RouteCard'

interface RoutePanelProps {
  plan: TripPlan
  labelOf: (routeId: string) => string
  selectedRouteId: string
  onSelectRoute: (routeId: string) => void
}

// Memoised so dragging the forecast slider does not re-render the route list.
export const RoutePanel = memo(function RoutePanel({
  plan,
  labelOf,
  selectedRouteId,
  onSelectRoute,
}: RoutePanelProps) {
  const text = describeRecommendation(plan, labelOf)
  const Icon = text.warning ? AlertTriangle : ShieldCheck

  return (
    <section aria-label="Route options" className="space-y-3">
      <div
        role="status"
        className={cx(
          'flex gap-3 rounded-lg border p-3',
          text.warning
            ? 'border-red-200 bg-red-50 text-red-900'
            : 'border-emerald-200 bg-emerald-50 text-emerald-900',
        )}
      >
        <Icon className="mt-0.5 size-5 shrink-0" />
        <div>
          <p className="font-semibold">{text.headline}</p>
          <p className="text-sm">{text.reason}</p>
        </div>
      </div>

      <ul className="space-y-2">
        {plan.routes.map((route) => (
          <li key={route.id}>
            <RouteCard
              route={route}
              label={labelOf(route.id)}
              recommended={route.id === plan.recommendation.route_id}
              selected={route.id === selectedRouteId}
              onSelect={() => onSelectRoute(route.id)}
            />
          </li>
        ))}
      </ul>
    </section>
  )
})
