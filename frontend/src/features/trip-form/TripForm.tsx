import { ArrowDownUp, Route } from 'lucide-react'
import { useId, useState, type FormEvent } from 'react'

import {
  SAMPLING_INTERVALS_MILES,
  type Place,
  type SamplingInterval,
  type TripRequest,
} from '@/api/types'
import { cx } from '@/lib/cx'
import { toDateTimeLocalValue } from '@/lib/format'
import { PlaceAutocomplete } from '@/features/trip-form/PlaceAutocomplete'

const MAX_LOAD_WEIGHT_LB = 80_000
const DEFAULT_LOAD_WEIGHT_LB = 40_000
const MAX_DAYS_AHEAD = 7

interface TripFormProps {
  isSubmitting: boolean
  onSubmit: (trip: TripRequest) => void
}

/** Departure limits as datetime-local values; fixed when the form mounts. */
function departureBounds(): { min: string; max: string } {
  const now = new Date()
  const latest = new Date(now.getTime() + MAX_DAYS_AHEAD * 24 * 60 * 60 * 1000)
  return { min: toDateTimeLocalValue(now), max: toDateTimeLocalValue(latest) }
}

function nextHour(): Date {
  const date = new Date()
  date.setHours(date.getHours() + 1, 0, 0, 0)
  return date
}

export function TripForm({ isSubmitting, onSubmit }: TripFormProps) {
  const departureId = useId()
  const weightId = useId()
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [departure, setDeparture] = useState(() => toDateTimeLocalValue(nextHour()))
  const [loadWeight, setLoadWeight] = useState(String(DEFAULT_LOAD_WEIGHT_LB))
  const [samplingInterval, setSamplingInterval] = useState<SamplingInterval>(25)
  // Remounting the autocompletes resets their text when the places are swapped.
  const [swapCount, setSwapCount] = useState(0)

  const weight = Number(loadWeight)
  const weightValid = Number.isFinite(weight) && weight > 0 && weight <= MAX_LOAD_WEIGHT_LB
  const canSubmit = origin !== null && destination !== null && weightValid && departure !== ''

  const [departureRange] = useState(departureBounds)

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!canSubmit) return
    onSubmit({
      origin: { lat: origin.lat, lon: origin.lon },
      destination: { lat: destination.lat, lon: destination.lon },
      departure_time: new Date(departure).toISOString(),
      load_weight_lb: weight,
      sampling_interval_miles: samplingInterval,
    })
  }

  function swapPlaces() {
    setOrigin(destination)
    setDestination(origin)
    setSwapCount((count) => count + 1)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" aria-label="Plan a trip">
      <div className="relative space-y-3">
        <PlaceAutocomplete
          key={`origin-${swapCount}`}
          label="Origin"
          placeholder="City or address"
          value={origin}
          onChange={setOrigin}
        />
        <PlaceAutocomplete
          key={`destination-${swapCount}`}
          label="Destination"
          placeholder="City or address"
          value={destination}
          onChange={setDestination}
        />
        <button
          type="button"
          onClick={swapPlaces}
          aria-label="Swap origin and destination"
          className="absolute top-[38px] right-[-14px] grid size-7 place-items-center rounded-full border border-slate-300 bg-white text-slate-500 shadow-xs hover:text-slate-800"
        >
          <ArrowDownUp className="size-3.5" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor={departureId} className="mb-1 block text-xs font-medium text-slate-600">
            Departure
          </label>
          <input
            id={departureId}
            type="datetime-local"
            required
            value={departure}
            min={departureRange.min}
            max={departureRange.max}
            onChange={(event) => setDeparture(event.target.value)}
            className="h-10 w-full rounded-md border border-slate-300 bg-white px-2 text-sm shadow-xs outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20"
          />
        </div>
        <div>
          <label htmlFor={weightId} className="mb-1 block text-xs font-medium text-slate-600">
            Load weight (lb)
          </label>
          <input
            id={weightId}
            type="number"
            inputMode="numeric"
            required
            min={1}
            max={MAX_LOAD_WEIGHT_LB}
            step={1}
            value={loadWeight}
            aria-invalid={!weightValid}
            onChange={(event) => setLoadWeight(event.target.value)}
            className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm shadow-xs outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 aria-invalid:border-red-400"
          />
        </div>
      </div>

      <fieldset>
        <legend className="mb-1 text-xs font-medium text-slate-600">
          Weather checkpoint every
        </legend>
        <div className="grid grid-cols-3 rounded-md border border-slate-300 bg-slate-100 p-0.5">
          {SAMPLING_INTERVALS_MILES.map((miles) => (
            <label
              key={miles}
              className={cx(
                'cursor-pointer rounded-[5px] py-1.5 text-center text-sm transition-colors',
                samplingInterval === miles
                  ? 'bg-white font-medium text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900',
              )}
            >
              <input
                type="radio"
                name="sampling-interval"
                value={miles}
                checked={samplingInterval === miles}
                onChange={() => setSamplingInterval(miles)}
                className="sr-only"
              />
              {miles} mi
            </label>
          ))}
        </div>
      </fieldset>

      <button
        type="submit"
        disabled={!canSubmit || isSubmitting}
        className="flex h-10 w-full items-center justify-center gap-2 rounded-md bg-slate-900 text-sm font-medium text-white transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
      >
        <Route className="size-4" />
        {isSubmitting ? 'Planning routes…' : 'Find safest route'}
      </button>
    </form>
  )
}
