/**
 * Test suite for DocumentList component.
 *
 * These tests verify the document list displays correctly with
 * search, sort, and accordion functionality.
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { DocumentList } from '../DocumentList'

// Mock the useDocumentLoader hook
vi.mock('@/hooks/useDocumentLoader', () => ({
  default: () => ({
    getDocuments: vi.fn(),
    getDocument: vi.fn(),
    uploadDocument: vi.fn(),
    deleteDocument: vi.fn()
  })
}))

// Mock the useStore hook
vi.mock('@/store', () => ({
  useStore: () => ({
    documentsData: mockDocuments,
    isDocumentsLoading: false,
    selectedDocument: null,
    setSelectedDocument: vi.fn()
  })
}))

const mockDocuments = [
  {
    document_id: 'doc-1',
    filename: 'test-document.pdf',
    file_type: '.pdf' as const,
    file_size: 1024000,
    upload_timestamp: '2026-03-19T10:30:00Z',
    chunk_count: 42,
    status: 'ready' as const,
    error_message: null
  },
  {
    document_id: 'doc-2',
    filename: 'another-doc.txt',
    file_type: '.txt' as const,
    file_size: 512000,
    upload_timestamp: '2026-03-19T11:00:00Z',
    chunk_count: 20,
    status: 'processing' as const,
    error_message: null
  }
]

describe('DocumentList Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render loading state with skeleton', () => {
    // Mock loading state
    vi.doMock('@/store', () => ({
      useStore: () => ({
        documentsData: null,
        isDocumentsLoading: true,
        selectedDocument: null,
        setSelectedDocument: vi.fn()
      })
    }))

    render(<DocumentList />)
    expect(screen.getByTestId(/skeleton/i)).toBeInTheDocument()
  })

  it('should render blank state when no documents exist', () => {
    vi.doMock('@/store', () => ({
      useStore: () => ({
        documentsData: [],
        isDocumentsLoading: false,
        selectedDocument: null,
        setSelectedDocument: vi.fn()
      })
    }))

    render(<DocumentList />)
    expect(screen.getByText(/no documents/i)).toBeInTheDocument()
  })

  it('should render list of documents', () => {
    render(<DocumentList />)

    expect(screen.getByText('test-document.pdf')).toBeInTheDocument()
    expect(screen.getByText('another-doc.txt')).toBeInTheDocument()
  })

  it('should filter documents by filename when searching', async () => {
    render(<DocumentList />)

    const searchInput = screen.getByPlaceholderText(/search documents/i)
    await userEvent.type(searchInput, 'test')

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument()
      expect(screen.queryByText('another-doc.txt')).not.toBeInTheDocument()
    })
  })

  it('should sort documents when sort option changes', async () => {
    render(<DocumentList />)

    const sortButton = screen.getByRole('button', { name: /sort/i })
    await userEvent.click(sortButton)

    const sortByNameOption = screen.getByText(/name/i)
    await userEvent.click(sortByNameOption)

    await waitFor(() => {
      const documents = screen.getAllByTestId(/document-item/i)
      expect(documents[0]).toHaveTextContent('another-doc.txt')
      expect(documents[1]).toHaveTextContent('test-document.pdf')
    })
  })

  it('should toggle accordion collapse/expand', async () => {
    render(<DocumentList />)

    const accordionButton = screen.getByRole('button', { name: /documents/i })
    expect(accordionButton).toHaveAttribute('aria-expanded', 'false')

    await userEvent.click(accordionButton)

    await waitFor(() => {
      expect(accordionButton).toHaveAttribute('aria-expanded', 'true')
    })
  })
})
