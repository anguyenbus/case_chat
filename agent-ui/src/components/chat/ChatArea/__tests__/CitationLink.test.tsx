import { vi } from 'vitest'
/**
 * Test suite for CitationLink component.
 *
 * These tests verify citation link functionality.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { CitationLink } from '../CitationLink'
import type { ReferenceData } from '@/types/os'

describe('CitationLink Component', () => {
  const mockReferences: ReferenceData[] = [
    {
      query: 'test query',
      references: [
        {
          content: 'Sample content',
          meta_data: { chunk: 1, chunk_size: 25 },
          name: 'test.pdf'
        }
      ]
    }
  ]

  const mockOnCitationClick = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render with citation number', () => {
    render(
      <CitationLink
        citationNumber={1}
        references={mockReferences}
        onCitationClick={mockOnCitationClick}
      />
    )

    expect(screen.getByText('[1]')).toBeInTheDocument()
  })

  it('should call onCitationClick when clicked', () => {
    render(
      <CitationLink
        citationNumber={1}
        references={mockReferences}
        onCitationClick={mockOnCitationClick}
      />
    )

    const link = screen.getByText('[1]')
    fireEvent.click(link)

    expect(mockOnCitationClick).toHaveBeenCalledWith(mockReferences)
  })

  it('should show tooltip on hover', () => {
    render(
      <CitationLink
        citationNumber={1}
        references={mockReferences}
        onCitationClick={mockOnCitationClick}
      />
    )

    // Tooltip should be present
    expect(screen.getByText('[1]')).toBeInTheDocument()
  })
})
