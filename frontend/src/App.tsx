import { useMutation } from '@tanstack/react-query'
import { Truck } from 'lucide-react'
import { lazy, Suspense, useCallback, useMemo, useState } from 'react'

import { planTrip } from '@/api/client'
import type { TripPlan, TripRequest } from '@/api/types'
import { routeLabel } from '@/lib/format'
import { ForecastControls } from '@/features/heatmap/ForecastControls'
import { positionAt, type HeatmapMode } from '@/features/heatmap/heatmapData'
import { useCorridorForecast } from '@/features/heatmap/useCorridorForecast'
import { RoutePanel } from '@/features/routes/RoutePanel'
import { TripForm } from '@/features/trip-form/TripForm'

// MapLibre is most of the bundle; loading it separately lets the form render first.
const HOUR_MS = 60 * 60 * 1000
const DEFAULT_MAX_HOUR = 48

const TripMap = lazy(() =>
  import('@/features/map/TripMap').then((module) => ({ default: module.TripMap })),
)

export function App() {
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)
  const [forecastHour, setForecastHour] = useState(0)
  const [heatmapMode, setHeatmapMode] = useState<HeatmapMode>('risk')
  const [heatmapVisible, setHeatmapVisible] = useState(true)

  const tripPlan = useMutation<TripPlan, Error, TripRequest>({
    mutationFn: planTrip,
    onSuccess: (plan) => {
      setSelectedRouteId(plan.recommendation.route_id)
      setForecastHour(0)
    },
  })
  const plan = tripPlan.data ?? null
  const corridor = useCorridorForecast(plan, tripPlan.submittedAt)

  const selectedRoute = plan?.routes.find((route) => route.id === selectedRouteId) ?? null
  const truckPosition = useMemo(
    () =>
      plan && selectedRoute
        ? positionAt(
            selectedRoute,
            new Date(Date.parse(plan.departure_time) + forecastHour * HOUR_MS),
          )
        : null,
    [plan, selectedRoute, forecastHour],
  )

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
            heatmap={{
              forecast: corridor.data,
              mode: heatmapMode,
              hour: forecastHour,
              visible: heatmapVisible,
            }}
            truckPosition={truckPosition}
          />
        </Suspense>
        {plan && (
          <ForecastControls
            departureTime={plan.departure_time}
            maxHour={corridor.data ? corridor.data.hours - 1 : DEFAULT_MAX_HOUR}
            hour={forecastHour}
            onHourChange={setForecastHour}
            mode={heatmapMode}
            onModeChange={setHeatmapMode}
            visible={heatmapVisible}
            onVisibleChange={setHeatmapVisible}
            status={corridor.status}
          />
        )}
      </main>
    </div>
  )
}
