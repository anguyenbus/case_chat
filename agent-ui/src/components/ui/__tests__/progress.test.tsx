/**
 * Test suite for Progress component.
 *
 * These tests verify the Progress component renders correctly
 * with proper accessibility attributes and visual updates.
 */

import { render, screen } from '@testing-library/react'
import { Progress } from '../progress'

describe('Progress Component', () => {
  it('should render with value 0', () => {
    render(<Progress value={0} />)

    const progressElement = screen.getByRole('progressbar')
    expect(progressElement).toBeInTheDocument()
    expect(progressElement).toHaveAttribute('aria-valuenow', '0')
  })

  it('should render with value 50', () => {
    render(<Progress value={50} />)

    const progressElement = screen.getByRole('progressbar')
    expect(progressElement).toBeInTheDocument()
    expect(progressElement).toHaveAttribute('aria-valuenow', '50')
  })

  it('should render with value 100', () => {
    render(<Progress value={100} />)

    const progressElement = screen.getByRole('progressbar')
    expect(progressElement).toBeInTheDocument()
    expect(progressElement).toHaveAttribute('aria-valuenow', '100')
  })

  it('should have proper accessibility attributes', () => {
    render(<Progress value={75} />)

    const progressElement = screen.getByRole('progressbar')
    expect(progressElement).toHaveAttribute('aria-valuemin', '0')
    expect(progressElement).toHaveAttribute('aria-valuemax', '100')
    expect(progressElement).toHaveAttribute('aria-valuenow', '75')
  })

  it('should apply custom className', () => {
    const { container } = render(
      <Progress value={50} className="custom-class" />
    )

    const progressElement = container.querySelector('.custom-class')
    expect(progressElement).toBeInTheDocument()
  })

  it('should clamp value to 100 when value exceeds maximum', () => {
    render(<Progress value={150} />)

    const progressElement = screen.getByRole('progressbar')
    expect(progressElement).toHaveAttribute('aria-valuenow', '100')
  })

  it('should clamp value to 0 when value is negative', () => {
    render(<Progress value={-10} />)

    const progressElement = screen.getByRole('progressbar')
    expect(progressElement).toHaveAttribute('aria-valuenow', '0')
  })
})
