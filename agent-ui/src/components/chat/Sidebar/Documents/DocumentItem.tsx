'use client'

/**
 * DocumentItem component.
 *
 * Individual document item in the document list following
 * the SessionItem pattern.
 *
 * @module Documents/DocumentItem
 */

import { type FC, useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { cn, truncateText } from '@/lib/utils'
import Icon from '@/components/ui/icon'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import DeleteDocumentModal from './DeleteDocumentModal'
import { toast } from 'sonner'
import { deleteDocumentAPI } from '@/api/documents'
import { useStore } from '@/store'
import type { Document } from '@/types/os'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '@/components/ui/tooltip'

/**
 * Props for DocumentItem component.
 */
export interface DocumentItemProps {
  /** Document data to display */
  document: Document
  /** Callback for document selection */
  onClick: () => void
  /** Callback for document deletion */
  onDelete: (documentId: string) => Promise<void>
  /** Whether this document is selected */
  isSelected: boolean
}

/**
 * File type icon mapping.
 */
const FILE_TYPE_ICONS: Record<string, string> = {
  '.pdf': 'file-text',
  '.txt': 'file',
  '.docx': 'file-text'
}

/**
 * Status badge color mapping.
 */
const STATUS_COLORS: Record<Document['status'], string> = {
  processing: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  ready: 'bg-green-500/10 text-green-500 border-green-500/20',
  error: 'bg-red-500/10 text-red-500 border-red-500/20'
}

/**
 * DocumentItem component for displaying individual documents.
 *
 * Features:
 * - File type icon (PDF, TXT, DOCX)
 * - Filename with truncation and tooltip
 * - File size display
 * - Status badge (processing, ready, error)
 * - Chunk count display
 * - Inline progress bar for processing documents
 * - Delete button on hover
 * - Selection state styling
 * - Click handler for document selection
 *
 * @example
 * ```tsx
 * <DocumentItem
 *   document={document}
 *   onClick={() => setSelectedDocument(document)}
 *   onDelete={handleDeleteDocument}
 *   isSelected={selectedDocument?.document_id === document.document_id}
 * />
 * ```
 */
const DocumentItem: FC<DocumentItemProps> = ({
  document,
  onClick,
  onDelete,
  isSelected
}) => {
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const { selectedEndpoint, authToken, documentsData, setDocumentsData } =
    useStore()

  /**
   * Formats file size for display.
   */
  const formattedFileSize = useMemo(() => {
    const sizeInMB = document.file_size / (1024 * 1024)
    if (sizeInMB < 1) {
      return `${(document.file_size / 1024).toFixed(1)} KB`
    }
    return `${sizeInMB.toFixed(1)} MB`
  }, [document.file_size])

  /**
   * Formats timestamp for display.
   */
  const formattedTimestamp = useMemo(() => {
    const date = new Date(document.upload_timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }, [document.upload_timestamp])

  /**
   * Handles document deletion.
   */
  const handleDeleteDocument = async () => {
    if (!selectedEndpoint) return

    setIsDeleting(true)
    try {
      await deleteDocumentAPI(selectedEndpoint, document.document_id, authToken)

      // Optimistically update store
      if (documentsData) {
        setDocumentsData(
          documentsData.filter(
            (doc) => doc.document_id !== document.document_id
          )
        )
      }

      toast.success('Document deleted successfully')
      setIsDeleteModalOpen(false)
    } catch (error) {
      toast.error(
        `Failed to delete document: ${error instanceof Error ? error.message : 'Unknown error'}`
      )
    } finally {
      setIsDeleting(false)
    }
  }

  /**
   * Handles delete button click (prevents document selection).
   */
  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsDeleteModalOpen(true)
  }

  return (
    <>
      <motion.div
        layout
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.2 }}
        className={cn(
          'group relative flex h-auto min-h-[72px] flex-col gap-2 rounded-lg px-3 py-2 transition-colors duration-200',
          isSelected
            ? 'cursor-default bg-primary/10'
            : 'cursor-pointer bg-background-secondary hover:bg-background-secondary/80'
        )}
        onClick={onClick}
      >
        <div className="flex items-center justify-between">
          <div className="flex flex-1 items-center gap-3 overflow-hidden">
            {/* File type icon */}
            <Icon
              type={FILE_TYPE_ICONS[document.file_type] || 'file'}
              size="sm"
              className="text-muted-foreground shrink-0"
            />

            {/* Document info */}
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <div className="flex items-center gap-2">
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <h4
                        className={cn(
                          'truncate text-sm font-medium',
                          isSelected && 'text-primary'
                        )}
                      >
                        {truncateText(document.filename, 20)}
                      </h4>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{document.filename}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>

                {/* Status badge */}
                <span
                  className={cn(
                    'shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase',
                    STATUS_COLORS[document.status]
                  )}
                >
                  {document.status}
                </span>
              </div>

              {/* Metadata */}
              <div className="text-muted-foreground flex items-center gap-2 text-xs">
                <span>{formattedFileSize}</span>
                <span>•</span>
                <span>{formattedTimestamp}</span>
                {document.chunk_count > 0 && (
                  <>
                    <span>•</span>
                    <span>{document.chunk_count} chunks</span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Delete button (visible on hover) */}
          <Button
            variant="ghost"
            size="icon"
            className="transform opacity-0 transition-all duration-200 ease-in-out group-hover:opacity-100"
            onClick={handleDeleteClick}
            aria-label="Delete document"
          >
            <Icon type="trash" size="xs" />
          </Button>
        </div>

        {/* Progress bar for processing documents */}
        {document.status === 'processing' && (
          <div className="mt-1">
            <Progress value={0} className="h-1" />
          </div>
        )}

        {/* Error message */}
        {document.status === 'error' && document.error_message && (
          <p className="mt-1 text-xs text-red-500">{document.error_message}</p>
        )}
      </motion.div>

      {/* Delete confirmation modal */}
      <DeleteDocumentModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onDelete={handleDeleteDocument}
        isDeleting={isDeleting}
      />
    </>
  )
}

export default DocumentItem
