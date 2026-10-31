import { RISK_LEVELS } from '@/api/types'
import { RISK_COLORS, RISK_LABELS } from '@/lib/risk'

export function RiskLegend() {
  return (
    <div className="absolute top-3 left-3 rounded-md bg-white/95 px-3 py-2 text-xs shadow-md">
      <p className="mb-1 font-medium text-slate-700">Weather risk</p>
      <ul className="space-y-0.5">
        {RISK_LEVELS.map((level) => (
          <li key={level} className="flex items-center gap-2 text-slate-600">
            <span
              aria-hidden
              className="inline-block h-1.5 w-4 rounded-full"
              style={{ backgroundColor: RISK_COLORS[level] }}
            />
            {RISK_LABELS[level]}
          </li>
        ))}
      </ul>
    </div>
  )
}
