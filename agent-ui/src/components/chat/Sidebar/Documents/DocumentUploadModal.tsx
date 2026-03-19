'use client'

/**
 * DocumentUploadModal component.
 *
 * Modal dialog for uploading documents with drag-and-drop support
 * and real-time progress tracking.
 *
 * @module Documents/DocumentUploadModal
 */

import { type FC, useState, useCallback } from 'react'
import { useStore } from '@/store'
import { uploadDocumentAPI } from '@/api/documents'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import DragDropZone from '@/components/ui/drag-drop-zone'
import type { UploadingFile } from '@/types/os'

/**
 * Props for DocumentUploadModal component.
 */
export interface DocumentUploadModalProps {
  /** Whether the modal is open */
  isOpen: boolean
  /** Callback to close the modal */
  onClose: () => void
  /** API endpoint for document upload */
  endpoint: string
  /** Authentication token */
  authToken: string
}

/**
 * Modal component for uploading documents.
 *
 * Features:
 * - Drag-and-drop file upload
 * - File picker as alternative
 * - Client-side file validation
 * - Real-time upload progress
 * - Multiple file support
 * - Error handling with toast notifications
 *
 * @example
 * ```tsx
 * <DocumentUploadModal
 *   isOpen={isModalOpen}
 *   onClose={() => setIsModalOpen(false)}
 *   endpoint="http://localhost:7777"
 *   authToken="token"
 * />
 * ```
 */
const DocumentUploadModal: FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  endpoint,
  authToken
}) => {
  const { setUploadingFiles } = useStore()
  const [isUploading, setIsUploading] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])

  /**
   * Handles file selection from drag-drop or file picker.
   */
  const handleFilesSelected = useCallback((files: File[]) => {
    setSelectedFiles((prev) => [...prev, ...files])
  }, [])

  /**
   * Handles document upload.
   */
  const handleUpload = useCallback(async () => {
    if (selectedFiles.length === 0) return

    setIsUploading(true)

    try {
      // Create uploading file entries
      const uploadingEntries: UploadingFile[] = selectedFiles.map((file) => ({
        id: `upload-${Date.now()}-${Math.random()}`,
        file,
        progress: 0,
        status: 'uploading'
      }))

      setUploadingFiles((prev) => [...prev, ...uploadingEntries])

      // Upload each file
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i]
        const uploadEntry = uploadingEntries[i]

        try {
          const response = await uploadDocumentAPI(endpoint, file, authToken)

          // Update upload entry status
          setUploadingFiles((prev) =>
            prev.map((uf) =>
              uf.id === uploadEntry.id
                ? { ...uf, progress: 100, status: 'processing' as const }
                : uf
            )
          )

          toast.success(`${file.name} uploaded successfully`)

          // Remove from uploading files after a delay
          setTimeout(() => {
            setUploadingFiles((prev) =>
              prev.filter((uf) => uf.id !== uploadEntry.id)
            )
          }, 3000)
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : 'Failed to upload document'

          // Mark as failed
          setUploadingFiles((prev) =>
            prev.map((uf) =>
              uf.id === uploadEntry.id
                ? { ...uf, status: 'error' as const }
                : uf
            )
          )

          toast.error(`Failed to upload ${file.name}: ${errorMessage}`)
        }
      }

      // Close modal and reset
      setSelectedFiles([])
      onClose()
    } catch (error) {
      toast.error(
        `Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      )
    } finally {
      setIsUploading(false)
    }
  }, [selectedFiles, endpoint, authToken, setUploadingFiles, onClose])

  /**
   * Removes a file from the selection.
   */
  const handleRemoveFile = useCallback((index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index))
  }, [])

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="font-geist sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Upload Document</DialogTitle>
          <DialogDescription>
            Upload PDF, TXT, or DOCX files (max 50MB each). Your documents will
            be processed and available for chat.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <DragDropZone
            onDrop={handleFilesSelected}
            acceptFileTypes={['.pdf', '.txt', '.docx']}
            maxFileSize={50}
          />

          {/* Selected files list */}
          {selectedFiles.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Selected Files:</p>
              <div className="max-h-40 space-y-1 overflow-y-auto">
                {selectedFiles.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between rounded-lg bg-background-secondary px-3 py-2"
                  >
                    <div className="flex flex-col">
                      <span className="text-sm font-medium">{file.name}</span>
                      <span className="text-muted-foreground text-xs">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveFile(index)}
                      disabled={isUploading}
                    >
                      Remove
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isUploading}
            className="rounded-xl border-border font-geist"
          >
            Cancel
          </Button>
          <Button
            onClick={handleUpload}
            disabled={selectedFiles.length === 0 || isUploading}
            className="rounded-xl font-geist"
          >
            {isUploading ? 'Uploading...' : 'Upload'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default DocumentUploadModal
