/**
 * useDocumentLoader hook.
 *
 * Custom hook for document management operations following
 * the useSessionLoader pattern.
 *
 * @module hooks/useDocumentLoader
 */

import { useCallback } from 'react'
import { useStore } from '@/store'
import {
  getDocumentsAPI,
  uploadDocumentAPI,
  deleteDocumentAPI
} from '@/api/documents'
import { toast } from 'sonner'
import type { UploadingFile } from '@/types/os'

/**
 * Custom hook for document management operations.
 *
 * Provides methods for:
 * - Fetching all documents
 * - Uploading new documents
 * - Deleting documents
 * - Managing loading states
 * - Optimistic UI updates
 *
 * @example
 * ```tsx
 * const { getDocuments, uploadDocument, deleteDocument } = useDocumentLoader()
 *
 * // Fetch documents
 * await getDocuments()
 *
 * // Upload document
 * await uploadDocument(file)
 *
 * // Delete document
 * await deleteDocument(documentId)
 * ```
 */
const useDocumentLoader = () => {
  const selectedEndpoint = useStore((state) => state.selectedEndpoint)
  const authToken = useStore((state) => state.authToken)
  const setIsDocumentsLoading = useStore((state) => state.setIsDocumentsLoading)
  const setDocumentsData = useStore((state) => state.setDocumentsData)
  const documentsData = useStore((state) => state.documentsData)
  const setUploadingFiles = useStore((state) => state.setUploadingFiles)

  /**
   * Fetches all documents from the backend.
   *
   * Updates the store with fetched documents and handles loading states.
   * Shows error toast on failure.
   */
  const getDocuments = useCallback(async () => {
    if (!selectedEndpoint) return

    try {
      setIsDocumentsLoading(true)

      const documents = await getDocumentsAPI(selectedEndpoint, authToken)
      setDocumentsData(documents)
    } catch (error) {
      console.error('[GET_DOCUMENTS] Error loading documents:', error)
      toast.error('Error loading documents')
      setDocumentsData([])
    } finally {
      setIsDocumentsLoading(false)
    }
  }, [selectedEndpoint, authToken, setDocumentsData, setIsDocumentsLoading])

  /**
   * Uploads a document to the backend.
   *
   * Creates an optimistic upload entry, uploads the file,
   * and updates the store with the result.
   *
   * @param file - File to upload
   * @returns Promise resolving to upload response
   */
  const uploadDocument = useCallback(
    async (file: File) => {
      if (!selectedEndpoint) {
        throw new Error('No endpoint selected')
      }

      // Create optimistic upload entry
      const uploadId = `upload-${Date.now()}-${Math.random()}`
      const uploadingFile: UploadingFile = {
        id: uploadId,
        file,
        progress: 0,
        status: 'uploading'
      }

      setUploadingFiles((prev) => [...prev, uploadingFile])

      try {
        const response = await uploadDocumentAPI(
          selectedEndpoint,
          file,
          authToken
        )

        // Update upload entry to processing
        setUploadingFiles((prev) =>
          prev.map((uf) =>
            uf.id === uploadId
              ? { ...uf, progress: 100, status: 'processing' }
              : uf
          )
        )

        toast.success(`${file.name} uploaded successfully`)

        // Remove upload entry after a delay
        setTimeout(() => {
          setUploadingFiles((prev) => prev.filter((uf) => uf.id !== uploadId))
        }, 3000)

        return response
      } catch (error) {
        // Mark as failed
        setUploadingFiles((prev) =>
          prev.map((uf) =>
            uf.id === uploadId ? { ...uf, status: 'error' } : uf
          )
        )

        const errorMessage =
          error instanceof Error ? error.message : 'Failed to upload document'
        toast.error(`Failed to upload ${file.name}: ${errorMessage}`)

        throw error
      }
    },
    [selectedEndpoint, authToken, setUploadingFiles]
  )

  /**
   * Deletes a document from the backend.
   *
   * Optimistically removes the document from the store,
   * calls the delete API, and reverts on failure.
   *
   * @param documentId - ID of document to delete
   */
  const deleteDocument = useCallback(
    async (documentId: string) => {
      if (!selectedEndpoint) {
        throw new Error('No endpoint selected')
      }

      // Optimistic update
      const previousDocuments = documentsData
      setDocumentsData(
        (prev) => prev?.filter((doc) => doc.document_id !== documentId) || null
      )

      try {
        await deleteDocumentAPI(selectedEndpoint, documentId, authToken)
        toast.success('Document deleted successfully')
      } catch (error) {
        // Revert on error
        setDocumentsData(previousDocuments)

        const errorMessage =
          error instanceof Error ? error.message : 'Failed to delete document'
        toast.error(`Failed to delete document: ${errorMessage}`)

        throw error
      }
    },
    [selectedEndpoint, authToken, documentsData, setDocumentsData]
  )

  return {
    getDocuments,
    uploadDocument,
    deleteDocument
  }
}

export default useDocumentLoader
