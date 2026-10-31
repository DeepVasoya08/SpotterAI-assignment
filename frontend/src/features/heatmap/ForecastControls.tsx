import { Eye, EyeOff, LoaderCircle, Pause, Play } from 'lucide-react'
import { useEffect, useId, useState } from 'react'

import { cx } from '@/lib/cx'
import { formatTime } from '@/lib/format'
import {
  HEATMAP_MODE_LABELS,
  HEATMAP_MODES,
  type HeatmapMode,
} from '@/features/heatmap/heatmapData'

const PLAYBACK_INTERVAL_MS = 600
const HOUR_MS = 60 * 60 * 1000

interface ForecastControlsProps {
  departureTime: string
  maxHour: number
  hour: number
  onHourChange: (hour: number) => void
  mode: HeatmapMode
  onModeChange: (mode: HeatmapMode) => void
  visible: boolean
  onVisibleChange: (visible: boolean) => void
  status: 'pending' | 'error' | 'success'
}

export function ForecastControls({
  departureTime,
  maxHour,
  hour,
  onHourChange,
  mode,
  onModeChange,
  visible,
  onVisibleChange,
  status,
}: ForecastControlsProps) {
  const sliderId = useId()
  const [playing, setPlaying] = useState(false)
  const ready = status === 'success'
  const time = formatTime(new Date(Date.parse(departureTime) + hour * HOUR_MS).toISOString())

  useEffect(() => {
    if (!playing) return
    const timer = window.setInterval(() => {
      if (hour >= maxHour) {
        setPlaying(false)
      } else {
        onHourChange(hour + 1)
      }
    }, PLAYBACK_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [playing, hour, maxHour, onHourChange])

  function togglePlayback() {
    if (!playing && hour >= maxHour) onHourChange(0)
    setPlaying(!playing)
  }

  return (
    <section
      aria-label="Corridor forecast"
      className="absolute right-3 bottom-8 left-3 rounded-lg bg-white/95 p-3 shadow-lg backdrop-blur sm:left-auto sm:w-[420px]"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-slate-800">Corridor forecast</p>
        <div className="flex items-center gap-1">
          <div
            role="radiogroup"
            aria-label="Heatmap layer"
            className="flex rounded-md bg-slate-100 p-0.5"
          >
            {HEATMAP_MODES.map((option) => (
              <button
                key={option}
                type="button"
                role="radio"
                aria-checked={mode === option}
                onClick={() => onModeChange(option)}
                className={cx(
                  'rounded px-2 py-0.5 text-xs',
                  mode === option
                    ? 'bg-white font-medium shadow-xs'
                    : 'text-slate-600 hover:text-slate-900',
                )}
              >
                {HEATMAP_MODE_LABELS[option]}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => onVisibleChange(!visible)}
            aria-label={visible ? 'Hide heatmap' : 'Show heatmap'}
            aria-pressed={visible}
            className="grid size-7 place-items-center rounded-md text-slate-600 hover:bg-slate-100"
          >
            {visible ? <Eye className="size-4" /> : <EyeOff className="size-4" />}
          </button>
        </div>
      </div>

      <div className="mt-2 flex items-center gap-3">
        <button
          type="button"
          onClick={togglePlayback}
          disabled={!ready}
          aria-label={playing ? 'Pause forecast playback' : 'Play forecast'}
          className="grid size-8 shrink-0 place-items-center rounded-full bg-slate-900 text-white disabled:bg-slate-300"
        >
          {playing ? <Pause className="size-4" /> : <Play className="size-4" />}
        </button>
        <div className="flex-1">
          <label htmlFor={sliderId} className="flex justify-between text-xs text-slate-600">
            <span className="font-medium text-slate-800">
              {hour === 0 ? 'At departure' : `+${hour} h`}
            </span>
            <span>{time}</span>
          </label>
          <input
            id={sliderId}
            type="range"
            min={0}
            max={maxHour}
            step={1}
            value={hour}
            disabled={!ready}
            aria-valuetext={`${hour} hours after departure, ${time}`}
            onChange={(event) => onHourChange(Number(event.target.value))}
            className="mt-1 w-full accent-slate-900"
          />
        </div>
      </div>

      {status === 'pending' && (
        <p className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
          <LoaderCircle className="size-3 animate-spin" />
          Loading corridor forecast…
        </p>
      )}
      {status === 'error' && (
        <p role="alert" className="mt-1 text-xs text-red-700">
          The corridor forecast is unavailable right now.
        </p>
      )}
    </section>
  )
}
