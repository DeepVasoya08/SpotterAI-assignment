import { useQuery } from '@tanstack/react-query'

import { fetchCorridorForecast } from '@/api/client'
import type { TripPlan } from '@/api/types'

/**
 * Loads the corridor forecast once a plan exists. Checkpoints are enough to describe
 * each route's corridor, so the full geometry is not sent back to the server.
 *
 * @param planKey changes whenever a new plan is made (the mutation's submit time).
 */
export function useCorridorForecast(plan: TripPlan | null, planKey: number) {
  return useQuery({
    queryKey: ['corridor-forecast', planKey],
    enabled: plan !== null,
    staleTime: Infinity,
    queryFn: ({ signal }) => {
      if (!plan) throw new Error('A trip plan is required.')
      return fetchCorridorForecast(
        {
          paths: plan.routes.map((route) =>
            route.checkpoints.map(({ lat, lon }) => ({ lat, lon })),
          ),
          departure_time: plan.departure_time,
          load_weight_lb: plan.load_weight_lb,
        },
        signal,
      )
    },
  })
}
