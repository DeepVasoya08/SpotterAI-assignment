import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Place } from '@/api/types'
import { TripForm } from '@/features/trip-form/TripForm'
import { jsonResponse, renderWithQueryClient } from '@/test/render'

const PLACES: Record<string, Place> = {
  chi: { id: 'chi', label: 'Chicago, IL, United States', lat: 41.88, lon: -87.63 },
  den: { id: 'den', label: 'Denver, CO, United States', lat: 39.74, lon: -104.99 },
}

function stubPlaceSearch() {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const query = new URL(String(input), 'http://localhost').searchParams.get('q') ?? ''
    const results = Object.values(PLACES).filter((place) =>
      place.label.toLowerCase().startsWith(query.toLowerCase()),
    )
    return Promise.resolve(jsonResponse({ results }))
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function choosePlace(label: string, text: string) {
  const user = userEvent.setup()
  await user.type(screen.getByRole('combobox', { name: label }), text)
  await user.click(await screen.findByRole('option', { name: new RegExp(text, 'i') }))
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('TripForm', () => {
  it('submits the selected places, weight and sampling interval', async () => {
    stubPlaceSearch()
    const onSubmit = vi.fn()
    renderWithQueryClient(<TripForm isSubmitting={false} onSubmit={onSubmit} />)
    const user = userEvent.setup()

    await choosePlace('Origin', 'Chicago')
    await choosePlace('Destination', 'Denver')
    await user.clear(screen.getByLabelText('Load weight (lb)'))
    await user.type(screen.getByLabelText('Load weight (lb)'), '42000')
    await user.click(screen.getByText('10 mi'))
    await user.click(screen.getByRole('button', { name: 'Find safest route' }))

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        origin: { lat: 41.88, lon: -87.63 },
        destination: { lat: 39.74, lon: -104.99 },
        load_weight_lb: 42000,
        sampling_interval_miles: 10,
      }),
    )
  })

  it('keeps submit disabled until both places are chosen', async () => {
    stubPlaceSearch()
    renderWithQueryClient(<TripForm isSubmitting={false} onSubmit={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Find safest route' })).toBeDisabled()
    await choosePlace('Origin', 'Chicago')
    expect(screen.getByRole('button', { name: 'Find safest route' })).toBeDisabled()
  })

  it('rejects a load above the legal maximum', async () => {
    stubPlaceSearch()
    renderWithQueryClient(<TripForm isSubmitting={false} onSubmit={vi.fn()} />)
    const user = userEvent.setup()

    await choosePlace('Origin', 'Chicago')
    await choosePlace('Destination', 'Denver')
    await user.clear(screen.getByLabelText('Load weight (lb)'))
    await user.type(screen.getByLabelText('Load weight (lb)'), '90000')

    expect(screen.getByRole('button', { name: 'Find safest route' })).toBeDisabled()
  })

  it('does not search until three characters are typed', async () => {
    const fetchMock = stubPlaceSearch()
    renderWithQueryClient(<TripForm isSubmitting={false} onSubmit={vi.fn()} />)

    await userEvent.setup().type(screen.getByRole('combobox', { name: 'Origin' }), 'Ch')

    await new Promise((resolve) => setTimeout(resolve, 400))
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('selects a suggestion with the keyboard', async () => {
    stubPlaceSearch()
    renderWithQueryClient(<TripForm isSubmitting={false} onSubmit={vi.fn()} />)
    const user = userEvent.setup()
    const origin = screen.getByRole('combobox', { name: 'Origin' })

    await user.type(origin, 'Den')
    await screen.findByRole('option')
    await user.keyboard('{ArrowDown}{Enter}')

    await waitFor(() => expect(origin).toHaveValue('Denver, CO, United States'))
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })
})
