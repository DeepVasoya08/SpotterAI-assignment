import { RISK_LEVELS, type RiskLevel } from '@/api/types'
import { RISK_COLORS, RISK_LABELS } from '@/lib/risk'

interface RiskBarProps {
  milesByLevel: Record<RiskLevel, number>
}

/** Share of the route's miles at each risk level. */
export function RiskBar({ milesByLevel }: RiskBarProps) {
  const total = RISK_LEVELS.reduce((sum, level) => sum + milesByLevel[level], 0)
  const description = RISK_LEVELS.filter((level) => milesByLevel[level] > 0)
    .map((level) => `${Math.round(milesByLevel[level])} mi ${RISK_LABELS[level]}`)
    .join(', ')

  return (
    <div
      role="img"
      aria-label={`Risk along route: ${description}`}
      className="flex h-2 w-full overflow-hidden rounded-full bg-slate-100"
    >
      {total > 0 &&
        RISK_LEVELS.map((level) =>
          milesByLevel[level] > 0 ? (
            <div
              key={level}
              style={{
                width: `${(milesByLevel[level] / total) * 100}%`,
                backgroundColor: RISK_COLORS[level],
              }}
            />
          ) : null,
        )}
    </div>
  )
}
