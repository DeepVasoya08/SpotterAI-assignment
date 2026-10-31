import { Clock, Flag, Star } from 'lucide-react'

import type { PlannedRoute, RiskLevel } from '@/api/types'
import { cx } from '@/lib/cx'
import { formatDuration, formatMiles, formatTime } from '@/lib/format'
import { RISK_COLORS, RISK_LABELS } from '@/lib/risk'
import { RiskBar } from '@/features/routes/RiskBar'

const HIGHLIGHTED_LEVELS: RiskLevel[] = ['no_travel', 'severe', 'high']

interface RouteCardProps {
  route: PlannedRoute
  label: string
  recommended: boolean
  selected: boolean
  onSelect: () => void
}

export function RouteCard({ route, label, recommended, selected, onSelect }: RouteCardProps) {
  const exposure = HIGHLIGHTED_LEVELS.filter((level) => route.summary.miles_by_level[level] >= 0.5)

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cx(
        'w-full rounded-lg border bg-white p-3 text-left transition-shadow',
        selected
          ? 'border-sky-500 shadow-md ring-1 ring-sky-500'
          : 'border-slate-200 hover:border-slate-300 hover:shadow-sm',
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-slate-900">{label}</span>
        {recommended && (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
            <Star className="size-3 fill-current" />
            Recommended
          </span>
        )}
      </div>

      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-600">
        <span>{formatMiles(route.distance_miles)}</span>
        <span className="inline-flex items-center gap-1">
          <Clock className="size-3.5" />
          {formatDuration(route.duration_s)}
        </span>
        <span className="inline-flex items-center gap-1">
          <Flag className="size-3.5" />
          {formatTime(route.arrival_time)}
        </span>
      </div>

      <div className="mt-3">
        <RiskBar milesByLevel={route.summary.miles_by_level} />
      </div>
      <p className="mt-2 text-xs text-slate-600">
        {exposure.length === 0
          ? 'No High or Severe weather expected'
          : exposure.map((level, index) => (
              <span key={level}>
                {index > 0 && ' · '}
                <span className="font-medium" style={{ color: RISK_COLORS[level] }}>
                  {formatMiles(route.summary.miles_by_level[level])} {RISK_LABELS[level]}
                </span>
              </span>
            ))}
      </p>
    </button>
  )
}
