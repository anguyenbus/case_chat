/**
 * Document type definitions for agent-ui document upload feature.
 *
 * These interfaces match the backend API response structure from
 * /home/an/projects/case_chat/src/case_chat/api/documents.py
 *
 * @module document-types
 */

/**
 * Document status indicating the current processing state.
 */
export type DocumentStatus = 'processing' | 'ready' | 'error'

/**
 * File extension types supported for document upload.
 */
export type FileType = '.pdf' | '.txt' | '.docx'

/**
 * Main Document interface matching backend API response.
 *
 * Corresponds to the document metadata returned by:
 * - GET /api/documents - list all documents
 * - GET /api/documents/{document_id} - get document details
 *
 * @see {@link https://github.com/fastapi/python-fastapi-boilerplate/blob/main/api/documents.py}
 */
export interface Document {
  /** Unique identifier for the document (UUID) */
  document_id: string
  /** Original filename of the uploaded document */
  filename: string
  /** File extension indicating document type */
  file_type: FileType
  /** File size in bytes */
  file_size: number
  /** ISO 8601 timestamp of when the document was uploaded */
  upload_timestamp: string
  /** Number of chunks the document was split into during processing */
  chunk_count: number
  /** Current processing status of the document */
  status: DocumentStatus
  /** Error message if status is 'error', null otherwise */
  error_message: string | null
}

/**
 * Processing stage for WebSocket progress updates.
 */
export type ProcessingStage =
  | 'parsing' // Extracting text from document (25%)
  | 'chunking' // Splitting text into chunks (50%)
  | 'embedding' // Generating vector embeddings (75%)
  | 'storing' // Saving to vector database (90%)
  | 'complete' // Processing finished successfully (100%)
  | 'error' // Processing failed

/**
 * WebSocket message structure for real-time progress updates.
 *
 * Received from WebSocket endpoint:
 * - WS /api/documents/progress?document_id={id}
 *
 * @see {@link https://github.com/fastapi/python-fastapi-boilerplate/blob/main/websocket/progress_manager.py}
 */
export interface ProcessingProgress {
  /** Document ID this progress update is for */
  document_id: string
  /** Current processing stage */
  stage: ProcessingStage
  /** Progress percentage (0-100) */
  progress_pct: number
  /** Human-readable progress message */
  message: string
  /** Error details if stage is 'error', null otherwise */
  error: string | null
}

/**
 * Upload status for local file tracking.
 */
export type UploadStatus = 'uploading' | 'processing' | 'ready' | 'error'

/**
 * Local file upload state during document upload process.
 *
 * Used to track files being uploaded before they receive
 * a document_id from the backend.
 */
export interface UploadingFile {
  /** Temporary local identifier for the upload */
  id: string
  /** File object being uploaded */
  file: File
  /** Upload progress percentage (0-100) */
  progress: number
  /** Current status of the upload */
  status: UploadStatus
}

/**
 * Chunk preview metadata for document details view.
 */
export interface ChunkPreview {
  /** Unique chunk identifier */
  chunk_id: string
  /** Chunk number in the document sequence */
  chunk_number: number
  /** Text content of the chunk */
  content: string
  /** Size of chunk in tokens */
  size: number
}

/**
 * Extended Document interface with additional metadata for details view.
 *
 * Extends the base Document interface with optional preview data
 * for displaying document chunks in the UI.
 */
export interface DocumentMetadata extends Document {
  /** Optional preview of document chunks */
  chunk_preview?: ChunkPreview[]
}

/**
 * API response for document upload endpoint.
 *
 * Returned by POST /api/documents/upload
 */
export interface UploadResponse {
  /** Generated document ID for the uploaded file */
  document_id: string
  /** Original filename */
  filename: string
  /** Initial processing status */
  status: string
  /** Success message */
  message: string
}

/**
 * API response for document list endpoint.
 *
 * Returned by GET /api/documents
 */
export interface DocumentListResponse {
  /** Array of document metadata */
  documents: Document[]
}

/**
 * API response for successful document deletion.
 *
 * Returned by DELETE /api/documents/{document_id}
 */
export interface DeleteResponse {
  /** Status indicator */
  status: string
  /** Success message */
  message: string
}
