/**
 * Document API client functions.
 *
 * Provides methods for document upload, retrieval, and deletion
 * with proper error handling and authentication.
 *
 * @module api/documents
 */

import type { Document, UploadResponse, DeleteResponse } from '@/types/os'

/**
 * Uploads a document to the backend.
 *
 * @param endpoint - Base API endpoint URL
 * @param file - File object to upload
 * @param authToken - Authentication token for API access
 * @returns Promise resolving to upload response with document_id
 * @throws Error if upload fails or file is invalid
 *
 * @example
 * ```typescript
 * const file = new File(['content'], 'document.pdf', { type: 'application/pdf' })
 * const response = await uploadDocumentAPI('http://localhost:7777', file, 'token')
 * console.log(response.document_id)
 * ```
 */
export async function uploadDocumentAPI(
  endpoint: string,
  file: File,
  authToken: string
): Promise<UploadResponse> {
  try {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${endpoint}/api/documents/upload`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`
      },
      body: formData
    })

    if (!response.ok) {
      const errorMsg = await response.text()
      throw new Error(
        `Failed to upload document: ${response.status} ${response.statusText} - ${errorMsg}`
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Upload failed: ${error.message}`)
    }
    throw new Error('Upload failed: Unknown error')
  }
}

/**
 * Fetches all documents from the backend.
 *
 * @param endpoint - Base API endpoint URL
 * @param authToken - Authentication token for API access
 * @returns Promise resolving to array of documents
 * @throws Error if fetch fails
 *
 * @example
 * ```typescript
 * const documents = await getDocumentsAPI('http://localhost:7777', 'token')
 * console.log(`Found ${documents.length} documents`)
 * ```
 */
export async function getDocumentsAPI(
  endpoint: string,
  authToken: string
): Promise<Document[]> {
  try {
    const response = await fetch(`${endpoint}/api/documents`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      const errorMsg = await response.text()
      throw new Error(
        `Failed to fetch documents: ${response.status} ${response.statusText} - ${errorMsg}`
      )
    }

    const data = await response.json()
    return data.documents || []
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Fetch failed: ${error.message}`)
    }
    throw new Error('Fetch failed: Unknown error')
  }
}

/**
 * Fetches a single document by ID.
 *
 * @param endpoint - Base API endpoint URL
 * @param documentId - Document ID to fetch
 * @param authToken - Authentication token for API access
 * @returns Promise resolving to document details
 * @throws Error if document not found or fetch fails
 *
 * @example
 * ```typescript
 * const document = await getDocumentAPI('http://localhost:7777', 'doc-123', 'token')
 * console.log(document.filename)
 * ```
 */
export async function getDocumentAPI(
  endpoint: string,
  documentId: string,
  authToken: string
): Promise<Document> {
  try {
    const response = await fetch(`${endpoint}/api/documents/${documentId}`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      const errorMsg = await response.text()
      throw new Error(
        `Failed to fetch document: ${response.status} ${response.statusText} - ${errorMsg}`
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Fetch failed: ${error.message}`)
    }
    throw new Error('Fetch failed: Unknown error')
  }
}

/**
 * Deletes a document by ID.
 *
 * @param endpoint - Base API endpoint URL
 * @param documentId - Document ID to delete
 * @param authToken - Authentication token for API access
 * @returns Promise resolving to delete response
 * @throws Error if document not found or delete fails
 *
 * @example
 * ```typescript
 * const result = await deleteDocumentAPI('http://localhost:7777', 'doc-123', 'token')
 * console.log(result.message)
 * ```
 */
export async function deleteDocumentAPI(
  endpoint: string,
  documentId: string,
  authToken: string
): Promise<DeleteResponse> {
  try {
    const response = await fetch(`${endpoint}/api/documents/${documentId}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      const errorMsg = await response.text()
      throw new Error(
        `Failed to delete document: ${response.status} ${response.statusText} - ${errorMsg}`
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Delete failed: ${error.message}`)
    }
    throw new Error('Delete failed: Unknown error')
  }
}
