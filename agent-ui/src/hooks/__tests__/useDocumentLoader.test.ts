import { vi } from 'vitest'
/**
 * Test suite for useDocumentLoader hook.
 *
 * These tests verify document management operations.
 */

import { renderHook, act, waitFor } from '@testing-library/react'
import { useStore } from '@/store'
import useDocumentLoader from '../useDocumentLoader'
import {
  getDocumentsAPI,
  uploadDocumentAPI,
  deleteDocumentAPI
} from '@/api/documents'
import { toast } from 'sonner'

// Mock dependencies
vi.mock('@/api/documents')
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn()
  }
}))

describe('useDocumentLoader Hook', () => {
  const mockEndpoint = 'http://localhost:7777'
  const mockAuthToken = 'test-token'

  beforeEach(() => {
    vi.clearAllMocks()
    // Reset store state
    const { setDocumentsData, setIsDocumentsLoading } = useStore.getState()
    setDocumentsData(null)
    setIsDocumentsLoading(false)
  })

  describe('getDocuments', () => {
    it('should fetch documents and update store', async () => {
      const mockDocuments = [
        {
          document_id: 'doc-1',
          filename: 'test.pdf',
          file_type: '.pdf' as const,
          file_size: 1024,
          upload_timestamp: '2026-03-19T10:00:00Z',
          chunk_count: 10,
          status: 'ready' as const,
          error_message: null
        }
      ]

      ;(getDocumentsAPI as jest.Mock).mockResolvedValue(mockDocuments)

      const { result } = renderHook(() => useDocumentLoader())

      await act(async () => {
        await result.current.getDocuments()
      })

      const { documentsData } = useStore.getState()
      expect(documentsData).toEqual(mockDocuments)
      expect(getDocumentsAPI).toHaveBeenCalledWith(mockEndpoint, mockAuthToken)
    })

    it('should set loading state during fetch', async () => {
      ;(getDocumentsAPI as jest.Mock).mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => resolve([]), 100)
          })
      )

      const { result } = renderHook(() => useDocumentLoader())

      act(() => {
        result.current.getDocuments()
      })

      const { isDocumentsLoading } = useStore.getState()
      expect(isDocumentsLoading).toBe(true)

      await waitFor(() => {
        const { isDocumentsLoading: loadingAfter } = useStore.getState()
        expect(loadingAfter).toBe(false)
      })
    })

    it('should handle fetch errors', async () => {
      const mockError = new Error('Failed to fetch')
      ;(getDocumentsAPI as jest.Mock).mockRejectedValue(mockError)

      const { result } = renderHook(() => useDocumentLoader())

      await act(async () => {
        await result.current.getDocuments()
      })

      expect(toast.error).toHaveBeenCalledWith('Error loading documents')
    })
  })

  describe('uploadDocument', () => {
    it('should upload document and update store', async () => {
      const mockFile = new File(['content'], 'test.pdf', {
        type: 'application/pdf'
      })
      const mockResponse = {
        document_id: 'doc-1',
        filename: 'test.pdf',
        status: 'processing',
        message: 'Document uploaded successfully'
      }

      ;(uploadDocumentAPI as jest.Mock).mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useDocumentLoader())

      await act(async () => {
        await result.current.uploadDocument(mockFile)
      })

      expect(uploadDocumentAPI).toHaveBeenCalledWith(
        mockEndpoint,
        mockFile,
        mockAuthToken
      )
    })

    it('should handle upload errors', async () => {
      const mockFile = new File(['content'], 'test.pdf', {
        type: 'application/pdf'
      })
      const mockError = new Error('Upload failed')

      ;(uploadDocumentAPI as jest.Mock).mockRejectedValue(mockError)

      const { result } = renderHook(() => useDocumentLoader())

      await act(async () => {
        await expect(result.current.uploadDocument(mockFile)).rejects.toThrow()
      })
    })
  })

  describe('deleteDocument', () => {
    it('should delete document and update store', async () => {
      const mockDocumentId = 'doc-1'
      const mockResponse = {
        status: 'success',
        message: 'Document deleted successfully'
      }

      // Set initial documents
      const { setDocumentsData } = useStore.getState()
      setDocumentsData([
        {
          document_id: mockDocumentId,
          filename: 'test.pdf',
          file_type: '.pdf' as const,
          file_size: 1024,
          upload_timestamp: '2026-03-19T10:00:00Z',
          chunk_count: 10,
          status: 'ready' as const,
          error_message: null
        }
      ])
      ;(deleteDocumentAPI as jest.Mock).mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useDocumentLoader())

      await act(async () => {
        await result.current.deleteDocument(mockDocumentId)
      })

      const { documentsData } = useStore.getState()
      expect(documentsData).toEqual([])
      expect(deleteDocumentAPI).toHaveBeenCalledWith(
        mockEndpoint,
        mockDocumentId,
        mockAuthToken
      )
    })

    it('should handle delete errors', async () => {
      const mockDocumentId = 'doc-1'
      const mockError = new Error('Delete failed')

      ;(deleteDocumentAPI as jest.Mock).mockRejectedValue(mockError)

      const { result } = renderHook(() => useDocumentLoader())

      await act(async () => {
        await expect(
          result.current.deleteDocument(mockDocumentId)
        ).rejects.toThrow()
      })
    })
  })
})
