import { useQuery } from '@tanstack/react-query'
import { LoaderCircle, MapPin } from 'lucide-react'
import { useId, useState, type KeyboardEvent } from 'react'

import { searchPlaces } from '@/api/client'
import type { Place } from '@/api/types'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { cx } from '@/lib/cx'

const MIN_QUERY_LENGTH = 3
const DEBOUNCE_MS = 250

interface PlaceAutocompleteProps {
  label: string
  placeholder: string
  value: Place | null
  onChange: (place: Place | null) => void
}

export function PlaceAutocomplete({ label, placeholder, value, onChange }: PlaceAutocompleteProps) {
  const inputId = useId()
  const listId = useId()
  const [text, setText] = useState(value?.label ?? '')
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)

  const query = useDebouncedValue(text.trim(), DEBOUNCE_MS)
  const searching = open && query.length >= MIN_QUERY_LENGTH && query !== value?.label
  const {
    data: places = [],
    isFetching,
    isError,
  } = useQuery({
    queryKey: ['places', query.toLowerCase()],
    queryFn: ({ signal }) => searchPlaces(query, signal),
    enabled: searching,
    staleTime: Infinity,
  })
  const showList = searching && (places.length > 0 || isError || !isFetching)

  function select(place: Place) {
    onChange(place)
    setText(place.label)
    setOpen(false)
    setActiveIndex(-1)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!showList || places.length === 0) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((index) => (index + 1) % places.length)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((index) => (index <= 0 ? places.length - 1 : index - 1))
    } else if (event.key === 'Enter') {
      const place = places[activeIndex]
      if (place) {
        event.preventDefault()
        select(place)
      }
    } else if (event.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div className="relative">
      <label htmlFor={inputId} className="mb-1 block text-xs font-medium text-slate-600">
        {label}
      </label>
      <div className="relative">
        <MapPin className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
        <input
          id={inputId}
          type="text"
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined}
          autoComplete="off"
          placeholder={placeholder}
          value={text}
          onChange={(event) => {
            setText(event.target.value)
            setOpen(true)
            setActiveIndex(-1)
            if (value) onChange(null)
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={handleKeyDown}
          className="h-10 w-full rounded-md border border-slate-300 bg-white pr-9 pl-9 text-sm shadow-xs outline-none placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20"
        />
        {isFetching && (
          <LoaderCircle
            aria-hidden
            className="absolute top-1/2 right-3 size-4 -translate-y-1/2 animate-spin text-slate-400"
          />
        )}
      </div>
      {showList && (
        <ul
          id={listId}
          role="listbox"
          aria-label={`${label} suggestions`}
          className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-md border border-slate-200 bg-white py-1 text-sm shadow-lg"
        >
          {isError && <li className="px-3 py-2 text-red-600">Place search is unavailable.</li>}
          {!isError && places.length === 0 && (
            <li className="px-3 py-2 text-slate-500">No matching places in the US.</li>
          )}
          {places.map((place, index) => (
            <li
              key={place.id}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              // mousedown fires before the input's blur closes the list.
              onMouseDown={(event) => {
                event.preventDefault()
                select(place)
              }}
              className={cx(
                'cursor-pointer px-3 py-2',
                index === activeIndex ? 'bg-sky-50 text-sky-900' : 'hover:bg-slate-50',
              )}
            >
              {place.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
