'use client'

/**
 * DeleteDocumentModal component.
 *
 * Confirmation modal for document deletion following the
 * DeleteSessionModal pattern.
 *
 * @module Documents/DeleteDocumentModal
 */

import { type FC } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'

/**
 * Props for DeleteDocumentModal component.
 */
export interface DeleteDocumentModalProps {
  /** Whether the modal is open */
  isOpen: boolean
  /** Callback to close the modal */
  onClose: () => void
  /** Callback to confirm deletion */
  onDelete: () => Promise<void>
  /** Whether deletion is in progress */
  isDeleting: boolean
}

/**
 * Delete confirmation modal for documents.
 *
 * Reuses the DeleteSessionModal pattern with:
 * - Warning message about permanent deletion
 * - Cancel and delete buttons
 * - Disabled state during deletion
 * - Dialog primitive for accessibility
 *
 * @example
 * ```tsx
 * <DeleteDocumentModal
 *   isOpen={isDeleteModalOpen}
 *   onClose={() => setIsDeleteModalOpen(false)}
 *   onDelete={handleDeleteDocument}
 *   isDeleting={isDeleting}
 * />
 * ```
 */
const DeleteDocumentModal: FC<DeleteDocumentModalProps> = ({
  isOpen,
  onClose,
  onDelete,
  isDeleting
}) => (
  <Dialog open={isOpen} onOpenChange={onClose}>
    <DialogContent className="font-geist">
      <DialogHeader>
        <DialogTitle>Confirm deletion</DialogTitle>
        <DialogDescription>
          This will permanently delete the document and all associated data.
          This action cannot be undone.
        </DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button
          variant="outline"
          className="rounded-xl border-border font-geist"
          onClick={onClose}
          disabled={isDeleting}
        >
          CANCEL
        </Button>
        <Button
          variant="destructive"
          onClick={onDelete}
          disabled={isDeleting}
          className="rounded-xl font-geist"
        >
          DELETE
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
)

export default DeleteDocumentModal
