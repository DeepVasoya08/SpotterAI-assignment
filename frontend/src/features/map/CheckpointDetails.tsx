import type { Checkpoint, Hazard } from '@/api/types'
import { formatMiles, formatTime } from '@/lib/format'
import { HAZARD_LABELS, RISK_COLORS, RISK_LABELS } from '@/lib/risk'

const HAZARDS: Hazard[] = ['wind', 'rain', 'snow']

interface CheckpointDetailsProps {
  checkpoint: Checkpoint
  routeLabel: string
}

export function CheckpointDetails({ checkpoint, routeLabel }: CheckpointDetailsProps) {
  const { weather, risk } = checkpoint
  const readings: Record<Hazard, string> = {
    wind: `${Math.round(weather.wind_speed_mph)} mph, gusts ${Math.round(weather.wind_gust_mph)}`,
    rain: `${weather.rain_in_per_hr.toFixed(2)} in/hr`,
    snow: `${weather.snow_in_per_hr.toFixed(2)} in/hr`,
  }

  return (
    <div className="w-56 text-slate-800">
      <p className="text-xs text-slate-500">
        {routeLabel} · mile {formatMiles(checkpoint.distance_miles).replace(' mi', '')}
      </p>
      <p className="font-semibold">Arrive {formatTime(checkpoint.eta)}</p>
      <p className="mt-1 flex items-center gap-1.5 text-sm font-medium">
        <span
          aria-hidden
          className="inline-block size-2.5 rounded-full"
          style={{ backgroundColor: RISK_COLORS[risk.level] }}
        />
        {RISK_LABELS[risk.level]} risk
      </p>
      <dl className="mt-2 space-y-1 text-xs">
        {HAZARDS.map((hazard) => (
          <div key={hazard} className="flex justify-between gap-2">
            <dt className="text-slate-500">{HAZARD_LABELS[hazard]}</dt>
            <dd className={risk.causes.includes(hazard) ? 'font-semibold' : undefined}>
              {readings[hazard]}
            </dd>
          </div>
        ))}
      </dl>
      {risk.load_adjusted && (
        <p className="mt-2 text-xs text-amber-700">Wind risk raised for this load weight.</p>
      )}
    </div>
  )
}
