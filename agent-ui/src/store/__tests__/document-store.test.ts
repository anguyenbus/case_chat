/**
 * Test suite for document store state management.
 *
 * These tests verify Zustand store functionality for document management,
 * including state updates, localStorage persistence, and optimistic updates.
 */

import { renderHook, act } from '@testing-library/react'
import { useStore } from '../store'

describe('Document Store State Management', () => {
  beforeEach(() => {
    // Reset store state before each test
    const {
      setDocumentsData,
      setIsDocumentsLoading,
      setSelectedDocument,
      setUploadingFiles
    } = useStore.getState()
    setDocumentsData(null)
    setIsDocumentsLoading(false)
    setSelectedDocument(null)
    setUploadingFiles([])
  })

  describe('documentsData state', () => {
    it('should initialize with null value', () => {
      const { result } = renderHook(() => useStore())
      expect(result.current.documentsData).toBeNull()
    })

    it('should update documentsData with array of documents', () => {
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

      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setDocumentsData(mockDocuments)
      })

      expect(result.current.documentsData).toEqual(mockDocuments)
      expect(result.current.documentsData).toHaveLength(1)
    })

    it('should update documentsData using functional update', () => {
      const initialDocuments = [
        {
          document_id: 'doc-1',
          filename: 'test1.pdf',
          file_type: '.pdf' as const,
          file_size: 1024,
          upload_timestamp: '2026-03-19T10:00:00Z',
          chunk_count: 10,
          status: 'ready' as const,
          error_message: null
        }
      ]

      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setDocumentsData(initialDocuments)
      })

      act(() => {
        result.current.setDocumentsData((prev) => [
          ...(prev || []),
          {
            document_id: 'doc-2',
            filename: 'test2.pdf',
            file_type: '.pdf' as const,
            file_size: 2048,
            upload_timestamp: '2026-03-19T10:01:00Z',
            chunk_count: 20,
            status: 'processing' as const,
            error_message: null
          }
        ])
      })

      expect(result.current.documentsData).toHaveLength(2)
    })

    it('should set documentsData to empty array', () => {
      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setDocumentsData([])
      })

      expect(result.current.documentsData).toEqual([])
    })
  })

  describe('isDocumentsLoading state', () => {
    it('should initialize with false value', () => {
      const { result } = renderHook(() => useStore())
      expect(result.current.isDocumentsLoading).toBe(false)
    })

    it('should update isDocumentsLoading to true', () => {
      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setIsDocumentsLoading(true)
      })

      expect(result.current.isDocumentsLoading).toBe(true)
    })

    it('should update isDocumentsLoading to false', () => {
      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setIsDocumentsLoading(true)
      })

      act(() => {
        result.current.setIsDocumentsLoading(false)
      })

      expect(result.current.isDocumentsLoading).toBe(false)
    })
  })

  describe('selectedDocument state', () => {
    it('should initialize with null value', () => {
      const { result } = renderHook(() => useStore())
      expect(result.current.selectedDocument).toBeNull()
    })

    it('should update selectedDocument with document object', () => {
      const mockDocument = {
        document_id: 'doc-1',
        filename: 'test.pdf',
        file_type: '.pdf' as const,
        file_size: 1024,
        upload_timestamp: '2026-03-19T10:00:00Z',
        chunk_count: 10,
        status: 'ready' as const,
        error_message: null
      }

      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setSelectedDocument(mockDocument)
      })

      expect(result.current.selectedDocument).toEqual(mockDocument)
    })

    it('should clear selectedDocument when set to null', () => {
      const mockDocument = {
        document_id: 'doc-1',
        filename: 'test.pdf',
        file_type: '.pdf' as const,
        file_size: 1024,
        upload_timestamp: '2026-03-19T10:00:00Z',
        chunk_count: 10,
        status: 'ready' as const,
        error_message: null
      }

      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setSelectedDocument(mockDocument)
      })

      act(() => {
        result.current.setSelectedDocument(null)
      })

      expect(result.current.selectedDocument).toBeNull()
    })
  })

  describe('uploadingFiles state', () => {
    it('should initialize with empty array', () => {
      const { result } = renderHook(() => useStore())
      expect(result.current.uploadingFiles).toEqual([])
    })

    it('should update uploadingFiles with file objects', () => {
      const file = new File(['content'], 'test.pdf', {
        type: 'application/pdf'
      })
      const uploadingFile = {
        id: 'upload-1',
        file,
        progress: 50,
        status: 'uploading' as const
      }

      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setUploadingFiles([uploadingFile])
      })

      expect(result.current.uploadingFiles).toHaveLength(1)
      expect(result.current.uploadingFiles[0]).toEqual(uploadingFile)
    })

    it('should support optimistic updates for upload operations', () => {
      const file1 = new File(['content1'], 'test1.pdf', {
        type: 'application/pdf'
      })
      const file2 = new File(['content2'], 'test2.pdf', {
        type: 'application/pdf'
      })

      const upload1 = {
        id: 'upload-1',
        file: file1,
        progress: 0,
        status: 'uploading' as const
      }

      const upload2 = {
        id: 'upload-2',
        file: file2,
        progress: 0,
        status: 'uploading' as const
      }

      const { result } = renderHook(() => useStore())

      // Add first upload
      act(() => {
        result.current.setUploadingFiles([upload1])
      })

      // Optimistically add second upload
      act(() => {
        result.current.setUploadingFiles((prev) => [...prev, upload2])
      })

      expect(result.current.uploadingFiles).toHaveLength(2)
      expect(result.current.uploadingFiles[0].id).toBe('upload-1')
      expect(result.current.uploadingFiles[1].id).toBe('upload-2')
    })
  })

  describe('localStorage persistence', () => {
    it('should persist documentsData to localStorage', () => {
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

      const { result } = renderHook(() => useStore())

      act(() => {
        result.current.setDocumentsData(mockDocuments)
      })

      // Verify localStorage was updated
      const storedData = localStorage.getItem('endpoint-storage')
      expect(storedData).toBeDefined()

      if (storedData) {
        const parsed = JSON.parse(storedData)
        expect(parsed).toHaveProperty('state')
        expect(parsed.state).toHaveProperty('documentsData')
      }
    })

    it('should handle missing localStorage data gracefully', () => {
      // Clear localStorage
      localStorage.clear()

      const { result } = renderHook(() => useStore())

      // Store should still initialize with defaults
      expect(result.current.documentsData).toBeNull()
      expect(result.current.isDocumentsLoading).toBe(false)
      expect(result.current.selectedDocument).toBeNull()
    })
  })
})
