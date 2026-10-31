import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ForecastControls } from '@/features/heatmap/ForecastControls'
import type { HeatmapMode } from '@/features/heatmap/heatmapData'

function Harness({ status = 'success' }: { status?: 'pending' | 'error' | 'success' }) {
  const [hour, setHour] = useState(0)
  const [mode, setMode] = useState<HeatmapMode>('risk')
  const [visible, setVisible] = useState(true)
  return (
    <ForecastControls
      departureTime="2026-11-01T15:00:00Z"
      maxHour={48}
      hour={hour}
      onHourChange={setHour}
      mode={mode}
      onModeChange={setMode}
      visible={visible}
      onVisibleChange={setVisible}
      status={status}
    />
  )
}

afterEach(() => {
  vi.useRealTimers()
})

describe('ForecastControls', () => {
  it('shows the hour offset as the slider moves', () => {
    render(<Harness />)
    const slider = screen.getByRole('slider')

    expect(screen.getByText('At departure')).toBeInTheDocument()
    fireEvent.change(slider, { target: { value: '3' } })

    expect(screen.getByText('+3 h')).toBeInTheDocument()
    expect(slider).toHaveAttribute(
      'aria-valuetext',
      expect.stringContaining('3 hours after departure'),
    )
  })

  it('switches the heatmap layer and visibility', async () => {
    render(<Harness />)
    const user = userEvent.setup()

    await user.click(screen.getByRole('radio', { name: 'Snow' }))
    await user.click(screen.getByRole('button', { name: 'Hide heatmap' }))

    expect(screen.getByRole('radio', { name: 'Snow' })).toHaveAttribute('aria-checked', 'true')
    expect(screen.getByRole('button', { name: 'Show heatmap' })).toBeInTheDocument()
  })

  it('plays through the forecast hours', () => {
    vi.useFakeTimers()
    render(<Harness />)

    act(() => {
      screen.getByRole('button', { name: 'Play forecast' }).click()
    })
    act(() => {
      vi.advanceTimersByTime(600)
    })
    act(() => {
      vi.advanceTimersByTime(600)
    })

    expect(screen.getByText('+2 h')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Pause forecast playback' })).toBeInTheDocument()
  })

  it('disables playback while the forecast loads', () => {
    render(<Harness status="pending" />)

    expect(screen.getByRole('slider')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Play forecast' })).toBeDisabled()
    expect(screen.getByText('Loading corridor forecast…')).toBeInTheDocument()
  })
})
