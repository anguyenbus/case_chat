import { vi } from 'vitest'
/**
 * Test suite for DocumentItem component.
 *
 * These tests verify document metadata display and interactions.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { DocumentItem } from '../DocumentItem'
import type { Document } from '@/types/os'

describe('DocumentItem Component', () => {
  const mockDocument: Document = {
    document_id: 'doc-1',
    filename: 'test-document.pdf',
    file_type: '.pdf',
    file_size: 1024000,
    upload_timestamp: '2026-03-19T10:30:00Z',
    chunk_count: 42,
    status: 'ready',
    error_message: null
  }

  const mockOnDelete = vi.fn()
  const mockOnClick = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render document filename', () => {
    render(
      <DocumentItem
        document={mockDocument}
        onDelete={mockOnDelete}
        onClick={mockOnClick}
        isSelected={false}
      />
    )

    expect(screen.getByText('test-document.pdf')).toBeInTheDocument()
  })

  it('should display file type icon for PDF', () => {
    const { container } = render(
      <DocumentItem
        document={mockDocument}
        onDelete={mockOnDelete}
        onClick={mockOnClick}
        isSelected={false}
      />
    )

    // Check for PDF icon (Lucide icon with data-lucide attribute)
    const pdfIcon = container.querySelector('[data-lucide="file-text"]')
    expect(pdfIcon).toBeInTheDocument()
  })

  it('should display status badge for ready status', () => {
    render(
      <DocumentItem
        document={mockDocument}
        onDelete={mockOnDelete}
        onClick={mockOnClick}
        isSelected={false}
      />
    )

    expect(screen.getByText('ready')).toBeInTheDocument()
  })

  it('should display status badge for processing status', () => {
    const processingDoc = { ...mockDocument, status: 'processing' as const }

    render(
      <DocumentItem
        document={processingDoc}
        onDelete={mockOnDelete}
        onClick={mockOnClick}
        isSelected={false}
      />
    )

    expect(screen.getByText('processing')).toBeInTheDocument()
  })

  it('should display status badge for error status', () => {
    const errorDoc = {
      ...mockDocument,
      status: 'error' as const,
      error_message: 'Processing failed'
    }

    render(
      <DocumentItem
        document={errorDoc}
        onDelete={mockOnDelete}
        onClick={mockOnClick}
        isSelected={false}
      />
    )

    expect(screen.getByText('error')).toBeInTheDocument()
  })

  it('should show delete button on hover', () => {
    const { container } = render(
      <DocumentItem
        document={mockDocument}
        onDelete={mockOnDelete}
        onClick={mockOnClick}
        isSelected={false}
      />
    )

    // Delete button should be in DOM but hidden (opacity-0)
    const deleteButton = container.querySelector(
      '[aria-label="Delete document"]'
    )
    expect(deleteButton).toBeInTheDocument()
  })

  it('should call onClick when document clicked', () => {
    render(
      <DocumentItem
        document={mockDocument}
        onDelete={mockOnDelete}
        onClick={mockOnClick}
        isSelected={false}
      />
    )

    const documentItem = screen.getByText('test-document.pdf').closest('div')
    if (documentItem) {
      fireEvent.click(documentItem)
      expect(mockOnClick).toHaveBeenCalled()
    }
  })

  it('should display chunk count', () => {
    render(
      <DocumentItem
        document={mockDocument}
        onDelete={mockOnDelete}
        onClick={mockOnClick}
        isSelected={false}
      />
    )

    expect(screen.getByText('42 chunks')).toBeInTheDocument()
  })
})
