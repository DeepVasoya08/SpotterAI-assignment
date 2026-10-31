import { useMutation } from '@tanstack/react-query'
import { Truck } from 'lucide-react'
import { lazy, Suspense, useCallback, useState } from 'react'

import { planTrip } from '@/api/client'
import type { TripPlan, TripRequest } from '@/api/types'
import { routeLabel } from '@/lib/format'
import { RoutePanel } from '@/features/routes/RoutePanel'
import { TripForm } from '@/features/trip-form/TripForm'

// MapLibre is most of the bundle; loading it separately lets the form render first.
const TripMap = lazy(() =>
  import('@/features/map/TripMap').then((module) => ({ default: module.TripMap })),
)

export function App() {
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)
  const tripPlan = useMutation<TripPlan, Error, TripRequest>({
    mutationFn: planTrip,
    onSuccess: (plan) => setSelectedRouteId(plan.recommendation.route_id),
  })
  const plan = tripPlan.data ?? null

  const labelOf = useCallback(
    (routeId: string) => routeLabel(plan?.routes.findIndex((route) => route.id === routeId) ?? 0),
    [plan],
  )

  return (
    <div className="flex h-dvh flex-col bg-slate-50 text-slate-900 lg:flex-row">
      <aside className="flex max-h-[55dvh] w-full shrink-0 flex-col overflow-y-auto border-b border-slate-200 bg-white lg:max-h-none lg:w-[400px] lg:border-r lg:border-b-0">
        <header className="flex items-center gap-2 border-b border-slate-200 px-5 py-4">
          <Truck className="size-5 text-sky-600" />
          <h1 className="text-base font-semibold">Weather-Aware Truck Routing</h1>
        </header>

        <div className="space-y-5 p-5">
          <TripForm isSubmitting={tripPlan.isPending} onSubmit={(trip) => tripPlan.mutate(trip)} />

          {tripPlan.isError && (
            <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-800">
              {tripPlan.error.message}
            </p>
          )}

          {plan && selectedRouteId && (
            <RoutePanel
              plan={plan}
              labelOf={labelOf}
              selectedRouteId={selectedRouteId}
              onSelectRoute={setSelectedRouteId}
            />
          )}
        </div>
      </aside>

      <main className="relative min-h-0 flex-1">
        <Suspense fallback={<div className="h-full w-full animate-pulse bg-slate-200" />}>
          <TripMap
            plan={plan}
            selectedRouteId={selectedRouteId}
            labelOf={labelOf}
            onSelectRoute={setSelectedRouteId}
          />
        </Suspense>
      </main>
    </div>
  )
}
