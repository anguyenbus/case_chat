/**
 * Test suite for Document type definitions.
 *
 * These tests verify that TypeScript interfaces correctly match
 * the backend API response structure for document management.
 */

import {
  Document,
  ProcessingProgress,
  UploadingFile,
  DocumentMetadata
} from '../document-types'

describe('Document Type Definitions', () => {
  describe('Document Interface', () => {
    it('should match backend API response structure', () => {
      const document: Document = {
        document_id: '123e4567-e89b-12d3-a456-426614174000',
        filename: 'test-document.pdf',
        file_type: '.pdf',
        file_size: 1024000,
        upload_timestamp: '2026-03-19T10:30:00Z',
        chunk_count: 42,
        status: 'ready',
        error_message: null
      }

      expect(document.document_id).toBeDefined()
      expect(document.filename).toBeDefined()
      expect(document.file_type).toBeDefined()
      expect(document.file_size).toBeDefined()
      expect(document.upload_timestamp).toBeDefined()
      expect(document.chunk_count).toBeDefined()
      expect(document.status).toBeDefined()
    })

    it('should accept valid status values', () => {
      const validStatuses: Array<Document['status']> = [
        'processing',
        'ready',
        'error'
      ]

      validStatuses.forEach((status) => {
        const document: Document = {
          document_id: 'test-id',
          filename: 'test.pdf',
          file_type: '.pdf',
          file_size: 1000,
          upload_timestamp: '2026-03-19T10:30:00Z',
          chunk_count: 0,
          status,
          error_message: null
        }
        expect(document.status).toBe(status)
      })
    })

    it('should allow null error_message for non-error status', () => {
      const document: Document = {
        document_id: 'test-id',
        filename: 'test.pdf',
        file_type: '.pdf',
        file_size: 1000,
        upload_timestamp: '2026-03-19T10:30:00Z',
        chunk_count: 0,
        status: 'ready',
        error_message: null
      }

      expect(document.error_message).toBeNull()
    })

    it('should allow string error_message for error status', () => {
      const document: Document = {
        document_id: 'test-id',
        filename: 'test.pdf',
        file_type: '.pdf',
        file_size: 1000,
        upload_timestamp: '2026-03-19T10:30:00Z',
        chunk_count: 0,
        status: 'error',
        error_message: 'Failed to process document'
      }

      expect(document.error_message).toBe('Failed to process document')
    })
  })

  describe('ProcessingProgress Interface', () => {
    it('should match WebSocket message structure', () => {
      const progress: ProcessingProgress = {
        document_id: 'test-id',
        stage: 'parsing',
        progress_pct: 25,
        message: 'Parsing document...',
        error: null
      }

      expect(progress.document_id).toBeDefined()
      expect(progress.stage).toBeDefined()
      expect(progress.progress_pct).toBeDefined()
      expect(progress.message).toBeDefined()
    })

    it('should accept valid stage values', () => {
      const validStages: Array<ProcessingProgress['stage']> = [
        'parsing',
        'chunking',
        'embedding',
        'storing',
        'complete',
        'error'
      ]

      validStages.forEach((stage) => {
        const progress: ProcessingProgress = {
          document_id: 'test-id',
          stage,
          progress_pct: 50,
          message: 'Processing...',
          error: null
        }
        expect(progress.stage).toBe(stage)
      })
    })

    it('should allow null error for non-error stages', () => {
      const progress: ProcessingProgress = {
        document_id: 'test-id',
        stage: 'parsing',
        progress_pct: 25,
        message: 'Parsing document...',
        error: null
      }

      expect(progress.error).toBeNull()
    })

    it('should allow string error for error stage', () => {
      const progress: ProcessingProgress = {
        document_id: 'test-id',
        stage: 'error',
        progress_pct: 0,
        message: 'Processing failed',
        error: 'Failed to parse document'
      }

      expect(progress.error).toBe('Failed to parse document')
    })
  })

  describe('UploadingFile Interface', () => {
    it('should represent local file upload state', () => {
      const file = new File(['test content'], 'test.pdf', {
        type: 'application/pdf'
      })
      const uploadingFile: UploadingFile = {
        id: 'local-upload-id',
        file,
        progress: 50,
        status: 'uploading'
      }

      expect(uploadingFile.id).toBeDefined()
      expect(uploadingFile.file).toBeDefined()
      expect(uploadingFile.progress).toBeDefined()
      expect(uploadingFile.status).toBeDefined()
    })

    it('should accept valid status values', () => {
      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })
      const validStatuses: Array<UploadingFile['status']> = [
        'uploading',
        'processing',
        'ready',
        'error'
      ]

      validStatuses.forEach((status) => {
        const uploadingFile: UploadingFile = {
          id: 'test-id',
          file,
          progress: 0,
          status
        }
        expect(uploadingFile.status).toBe(status)
      })
    })

    it('should track progress from 0 to 100', () => {
      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })

      const startProgress: UploadingFile = {
        id: 'test-id',
        file,
        progress: 0,
        status: 'uploading'
      }

      const midProgress: UploadingFile = {
        id: 'test-id',
        file,
        progress: 50,
        status: 'processing'
      }

      const completeProgress: UploadingFile = {
        id: 'test-id',
        file,
        progress: 100,
        status: 'ready'
      }

      expect(startProgress.progress).toBe(0)
      expect(midProgress.progress).toBe(50)
      expect(completeProgress.progress).toBe(100)
    })
  })

  describe('DocumentMetadata Interface', () => {
    it('should extend Document with additional fields', () => {
      const metadata: DocumentMetadata = {
        document_id: 'test-id',
        filename: 'test.pdf',
        file_type: '.pdf',
        file_size: 1000,
        upload_timestamp: '2026-03-19T10:30:00Z',
        chunk_count: 10,
        status: 'ready',
        error_message: null,
        chunk_preview: [
          {
            chunk_id: 'chunk-1',
            chunk_number: 1,
            content: 'Sample document content...',
            size: 25
          }
        ]
      }

      expect(metadata.document_id).toBeDefined()
      expect(metadata.chunk_preview).toBeDefined()
      expect(metadata.chunk_preview?.[0].chunk_id).toBeDefined()
      expect(metadata.chunk_preview?.[0].chunk_number).toBeDefined()
      expect(metadata.chunk_preview?.[0].content).toBeDefined()
      expect(metadata.chunk_preview?.[0].size).toBeDefined()
    })

    it('should allow optional chunk_preview', () => {
      const metadata: DocumentMetadata = {
        document_id: 'test-id',
        filename: 'test.pdf',
        file_type: '.pdf',
        file_size: 1000,
        upload_timestamp: '2026-03-19T10:30:00Z',
        chunk_count: 10,
        status: 'ready',
        error_message: null
      }

      expect(metadata.chunk_preview).toBeUndefined()
    })

    it('should include all Document fields', () => {
      const metadata: DocumentMetadata = {
        document_id: 'test-id',
        filename: 'test.pdf',
        file_type: '.pdf',
        file_size: 1000,
        upload_timestamp: '2026-03-19T10:30:00Z',
        chunk_count: 10,
        status: 'ready',
        error_message: null
      }

      // Verify it can be used as a Document
      const document: Document = metadata
      expect(document.document_id).toBe('test-id')
      expect(document.filename).toBe('test.pdf')
    })
  })
})
