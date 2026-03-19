'use client'

/**
 * DocumentBlankState component.
 *
 * Blank state shown when no documents exist.
 *
 * @module Documents/DocumentBlankState
 */

import { type FC } from 'react'
import { Button } from '@/components/ui/button'
import Icon from '@/components/ui/icon'

/**
 * Props for DocumentBlankState component.
 */
export interface DocumentBlankStateProps {
  /** Callback to trigger document upload (optional, not used in current implementation) */
  onUpload?: () => void
}

/**
 * Blank state component for empty document list.
 *
 * Displays:
 * - Icon indicating no documents
 * - Message explaining upload functionality
 * - Upload button to open upload modal
 *
 * @example
 * ```tsx
 * <DocumentBlankState onUpload={() => setIsUploadModalOpen(true)} />
 * ```
 */
const DocumentBlankState: FC<DocumentBlankStateProps> = ({ onUpload }) => {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-background-secondary/30 px-4 py-6 text-center">
      <Icon type="file-text" size="md" className="text-muted-foreground mb-2" />
      <p className="text-muted-foreground text-xs">
        No documents. Use the upload button above to get started.
      </p>
    </div>
  )
}

export default DocumentBlankState
