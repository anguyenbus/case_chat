import { vi } from 'vitest'
/**
 * Test suite for CitationPanel component.
 *
 * These tests verify the citation panel displays references correctly.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { CitationPanel } from '../CitationPanel'
import type { ReferenceData } from '@/types/os'

describe('CitationPanel Component', () => {
  const mockReferences: ReferenceData[] = [
    {
      query: 'test query',
      references: [
        {
          content: 'Sample document content for testing...',
          meta_data: {
            chunk: 1,
            chunk_size: 25
          },
          name: 'test-document.pdf'
        }
      ],
      time: 100
    }
  ]

  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render when open', () => {
    render(
      <CitationPanel
        isOpen={true}
        onClose={mockOnClose}
        references={mockReferences}
      />
    )

    expect(screen.getByText('References')).toBeInTheDocument()
  })

  it('should not render when closed', () => {
    render(
      <CitationPanel
        isOpen={false}
        onClose={mockOnClose}
        references={mockReferences}
      />
    )

    expect(screen.queryByText('References')).not.toBeInTheDocument()
  })

  it('should display document name', () => {
    render(
      <CitationPanel
        isOpen={true}
        onClose={mockOnClose}
        references={mockReferences}
      />
    )

    expect(screen.getByText('test-document.pdf')).toBeInTheDocument()
  })

  it('should display chunk content', () => {
    render(
      <CitationPanel
        isOpen={true}
        onClose={mockOnClose}
        references={mockReferences}
      />
    )

    expect(
      screen.getByText('Sample document content for testing...')
    ).toBeInTheDocument()
  })

  it('should call onClose when close button clicked', () => {
    render(
      <CitationPanel
        isOpen={true}
        onClose={mockOnClose}
        references={mockReferences}
      />
    )

    const closeButton = screen.getByRole('button', { name: /close/i })
    fireEvent.click(closeButton)

    expect(mockOnClose).toHaveBeenCalled()
  })
})
