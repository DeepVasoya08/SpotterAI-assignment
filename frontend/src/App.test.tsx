import { screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { App } from '@/App'
import { renderWithQueryClient } from '@/test/render'

// MapLibre needs WebGL, which jsdom does not provide.
vi.mock('@/features/map/TripMap', () => ({ TripMap: () => <div data-testid="map" /> }))

describe('App', () => {
  it('renders the trip form and the map', async () => {
    renderWithQueryClient(<App />)

    expect(screen.getByRole('heading', { name: 'Weather-Aware Truck Routing' })).toBeInTheDocument()
    expect(screen.getByRole('form', { name: 'Plan a trip' })).toBeInTheDocument()
    expect(await screen.findByTestId('map')).toBeInTheDocument()
  })
})
