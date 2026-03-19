import { vi } from 'vitest'
/**
 * Test suite for DragDropZone component.
 *
 * These tests verify drag-and-drop functionality and file validation.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { DragDropZone } from '../drag-drop-zone'

describe('DragDropZone Component', () => {
  const mockOnDrop = vi.fn()
  const acceptFileTypes = ['.pdf', '.txt', '.docx']
  const maxFileSize = 50 // 50MB

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render drag-drop zone', () => {
    render(
      <DragDropZone
        onDrop={mockOnDrop}
        acceptFileTypes={acceptFileTypes}
        maxFileSize={maxFileSize}
      />
    )

    expect(screen.getByText(/drop your files here/i)).toBeInTheDocument()
  })

  it('should change border color on drag over', () => {
    const { container } = render(
      <DragDropZone
        onDrop={mockOnDrop}
        acceptFileTypes={acceptFileTypes}
        maxFileSize={maxFileSize}
      />
    )

    const zone = container.querySelector('[draggable="true"]')
    expect(zone).toBeInTheDocument()

    if (zone) {
      fireEvent.dragOver(zone)
      // Check for visual feedback (border color change)
      expect(zone).toHaveClass('border-primary')
    }
  })

  it('should reset border color on drag leave', () => {
    const { container } = render(
      <DragDropZone
        onDrop={mockOnDrop}
        acceptFileTypes={acceptFileTypes}
        maxFileSize={maxFileSize}
      />
    )

    const zone = container.querySelector('[draggable="true"]')
    if (zone) {
      fireEvent.dragOver(zone)
      fireEvent.dragLeave(zone)

      // Border should reset
      expect(zone).not.toHaveClass('border-primary')
    }
  })

  it('should call onDrop with valid files', () => {
    const { container } = render(
      <DragDropZone
        onDrop={mockOnDrop}
        acceptFileTypes={acceptFileTypes}
        maxFileSize={maxFileSize}
      />
    )

    const zone = container.querySelector('[draggable="true"]')
    if (zone) {
      const file = new File(['content'], 'test.pdf', {
        type: 'application/pdf'
      })
      const dropEvent = new Event('drop', { bubbles: true })
      Object.defineProperty(dropEvent, 'dataTransfer', {
        value: { files: [file] }
      })

      fireEvent(zone, dropEvent)

      expect(mockOnDrop).toHaveBeenCalledWith([file])
    }
  })

  it('should reject invalid file types', () => {
    const { container } = render(
      <DragDropZone
        onDrop={mockOnDrop}
        acceptFileTypes={acceptFileTypes}
        maxFileSize={maxFileSize}
      />
    )

    const zone = container.querySelector('[draggable="true"]')
    if (zone) {
      const file = new File(['content'], 'test.exe', {
        type: 'application/exe'
      })
      const dropEvent = new Event('drop', { bubbles: true })
      Object.defineProperty(dropEvent, 'dataTransfer', {
        value: { files: [file] }
      })

      fireEvent(zone, dropEvent)

      expect(mockOnDrop).not.toHaveBeenCalled()
    }
  })

  it('should reject files exceeding max size', () => {
    const { container } = render(
      <DragDropZone
        onDrop={mockOnDrop}
        acceptFileTypes={acceptFileTypes}
        maxFileSize={maxFileSize}
      />
    )

    const zone = container.querySelector('[draggable="true"]')
    if (zone) {
      // Create a file larger than 50MB
      const largeContent = new Array(51 * 1024 * 1024).fill('x').join('')
      const file = new File([largeContent], 'large.pdf', {
        type: 'application/pdf'
      })

      const dropEvent = new Event('drop', { bubbles: true })
      Object.defineProperty(dropEvent, 'dataTransfer', {
        value: { files: [file] }
      })

      fireEvent(zone, dropEvent)

      expect(mockOnDrop).not.toHaveBeenCalled()
    }
  })
})
