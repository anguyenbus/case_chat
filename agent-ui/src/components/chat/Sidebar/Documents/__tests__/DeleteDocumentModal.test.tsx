import { vi } from 'vitest'
/**
 * Test suite for DeleteDocumentModal component.
 *
 * These tests verify the delete confirmation modal works correctly.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import DeleteDocumentModal from '../DeleteDocumentModal'

describe('DeleteDocumentModal Component', () => {
  const mockOnClose = vi.fn()
  const mockOnDelete = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render when open', () => {
    render(
      <DeleteDocumentModal
        isOpen={true}
        onClose={mockOnClose}
        onDelete={mockOnDelete}
        isDeleting={false}
      />
    )

    expect(screen.getByText('Confirm deletion')).toBeInTheDocument()
  })

  it('should show warning message', () => {
    render(
      <DeleteDocumentModal
        isOpen={true}
        onClose={mockOnClose}
        onDelete={mockOnDelete}
        isDeleting={false}
      />
    )

    expect(
      screen.getByText(/permanently delete the document/i)
    ).toBeInTheDocument()
  })

  it('should call onClose when cancel button clicked', () => {
    render(
      <DeleteDocumentModal
        isOpen={true}
        onClose={mockOnClose}
        onDelete={mockOnDelete}
        isDeleting={false}
      />
    )

    const cancelButton = screen.getByText('CANCEL')
    fireEvent.click(cancelButton)

    expect(mockOnClose).toHaveBeenCalled()
    expect(mockOnDelete).not.toHaveBeenCalled()
  })

  it('should call onDelete when delete button clicked', () => {
    render(
      <DeleteDocumentModal
        isOpen={true}
        onClose={mockOnClose}
        onDelete={mockOnDelete}
        isDeleting={false}
      />
    )

    const deleteButton = screen.getByText('DELETE')
    fireEvent.click(deleteButton)

    expect(mockOnDelete).toHaveBeenCalled()
  })

  it('should disable buttons when deleting', () => {
    render(
      <DeleteDocumentModal
        isOpen={true}
        onClose={mockOnClose}
        onDelete={mockOnDelete}
        isDeleting={true}
      />
    )

    const cancelButton = screen.getByText('CANCEL')
    const deleteButton = screen.getByText('DELETE')

    expect(cancelButton).toBeDisabled()
    expect(deleteButton).toBeDisabled()
  })
})
