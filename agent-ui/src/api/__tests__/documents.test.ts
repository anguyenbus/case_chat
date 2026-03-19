import { vi } from 'vitest'
/**
 * Test suite for document API client functions.
 *
 * These tests verify API calls for document upload, retrieval, and deletion.
 */

import {
  uploadDocumentAPI,
  getDocumentsAPI,
  getDocumentAPI,
  deleteDocumentAPI
} from '../documents'
import { Document, UploadResponse, DeleteResponse } from '@/types/os'

// Mock fetch globally
global.fetch = vi.fn()

describe('Document API Client Functions', () => {
  const mockEndpoint = 'http://localhost:7777'
  const mockAuthToken = 'test-token'

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('uploadDocumentAPI', () => {
    it('should upload document with FormData', async () => {
      const mockFile = new File(['test content'], 'test.pdf', {
        type: 'application/pdf'
      })

      const mockResponse: UploadResponse = {
        document_id: 'doc-123',
        filename: 'test.pdf',
        status: 'processing',
        message: 'Document uploaded successfully'
      }

      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await uploadDocumentAPI(
        mockEndpoint,
        mockFile,
        mockAuthToken
      )

      expect(global.fetch).toHaveBeenCalledTimes(1)
      expect(global.fetch).toHaveBeenCalledWith(
        `${mockEndpoint}/api/documents/upload`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            Authorization: `Bearer ${mockAuthToken}`
          },
          body: expect.any(FormData)
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('should include authentication token in request', async () => {
      const mockFile = new File(['test'], 'test.pdf', {
        type: 'application/pdf'
      })

      const mockResponse: UploadResponse = {
        document_id: 'doc-123',
        filename: 'test.pdf',
        status: 'processing',
        message: 'Document uploaded successfully'
      }

      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      await uploadDocumentAPI(mockEndpoint, mockFile, mockAuthToken)

      const fetchCall = (global.fetch as jest.Mock).mock.calls[0]
      expect(fetchCall[1].headers.Authorization).toBe(`Bearer ${mockAuthToken}`)
    })

    it('should handle file too large error (413)', async () => {
      const mockFile = new File(['test'], 'test.pdf', {
        type: 'application/pdf'
      })

      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 413,
        statusText: 'Payload Too Large',
        text: async () => 'File too large. Maximum size is 50MB'
      })

      await expect(
        uploadDocumentAPI(mockEndpoint, mockFile, mockAuthToken)
      ).rejects.toThrow()
    })

    it('should handle invalid file type error (400)', async () => {
      const mockFile = new File(['test'], 'test.exe', {
        type: 'application/exe'
      })

      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        text: async () => 'Invalid file type'
      })

      await expect(
        uploadDocumentAPI(mockEndpoint, mockFile, mockAuthToken)
      ).rejects.toThrow()
    })

    it('should handle network errors gracefully', async () => {
      const mockFile = new File(['test'], 'test.pdf', {
        type: 'application/pdf'
      })

      ;(global.fetch as jest.Mock).mockRejectedValueOnce(
        new Error('Network error')
      )

      await expect(
        uploadDocumentAPI(mockEndpoint, mockFile, mockAuthToken)
      ).rejects.toThrow('Network error')
    })
  })

  describe('getDocumentsAPI', () => {
    it('should fetch list of documents', async () => {
      const mockDocuments: Document[] = [
        {
          document_id: 'doc-1',
          filename: 'test1.pdf',
          file_type: '.pdf',
          file_size: 1024,
          upload_timestamp: '2026-03-19T10:00:00Z',
          chunk_count: 10,
          status: 'ready',
          error_message: null
        },
        {
          document_id: 'doc-2',
          filename: 'test2.txt',
          file_type: '.txt',
          file_size: 512,
          upload_timestamp: '2026-03-19T10:01:00Z',
          chunk_count: 5,
          status: 'processing',
          error_message: null
        }
      ]

      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ documents: mockDocuments })
      })

      const result = await getDocumentsAPI(mockEndpoint, mockAuthToken)

      expect(global.fetch).toHaveBeenCalledTimes(1)
      expect(global.fetch).toHaveBeenCalledWith(
        `${mockEndpoint}/api/documents`,
        expect.objectContaining({
          headers: {
            Authorization: `Bearer ${mockAuthToken}`
          }
        })
      )
      expect(result).toEqual(mockDocuments)
    })

    it('should return empty array when no documents exist', async () => {
      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ documents: [] })
      })

      const result = await getDocumentsAPI(mockEndpoint, mockAuthToken)

      expect(result).toEqual([])
    })
  })

  describe('getDocumentAPI', () => {
    it('should fetch single document details', async () => {
      const mockDocument: Document = {
        document_id: 'doc-1',
        filename: 'test.pdf',
        file_type: '.pdf',
        file_size: 1024,
        upload_timestamp: '2026-03-19T10:00:00Z',
        chunk_count: 10,
        status: 'ready',
        error_message: null
      }

      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockDocument
      })

      const result = await getDocumentAPI(mockEndpoint, 'doc-1', mockAuthToken)

      expect(global.fetch).toHaveBeenCalledWith(
        `${mockEndpoint}/api/documents/doc-1`,
        expect.objectContaining({
          headers: {
            Authorization: `Bearer ${mockAuthToken}`
          }
        })
      )
      expect(result).toEqual(mockDocument)
    })

    it('should handle document not found (404)', async () => {
      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ error: 'Document not found' })
      })

      await expect(
        getDocumentAPI(mockEndpoint, 'nonexistent', mockAuthToken)
      ).rejects.toThrow()
    })
  })

  describe('deleteDocumentAPI', () => {
    it('should delete document successfully', async () => {
      const mockResponse: DeleteResponse = {
        status: 'success',
        message: 'Document deleted successfully'
      }

      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const result = await deleteDocumentAPI(
        mockEndpoint,
        'doc-1',
        mockAuthToken
      )

      expect(global.fetch).toHaveBeenCalledWith(
        `${mockEndpoint}/api/documents/doc-1`,
        expect.objectContaining({
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${mockAuthToken}`
          }
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('should handle document not found on delete (404)', async () => {
      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ error: 'Document not found' })
      })

      await expect(
        deleteDocumentAPI(mockEndpoint, 'nonexistent', mockAuthToken)
      ).rejects.toThrow()
    })
  })
})
