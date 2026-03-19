'use client'

/**
 * DragDropZone component for file upload.
 *
 * Provides an interactive drag-and-drop zone with visual feedback
 * and client-side file validation for type and size.
 *
 * @module ui/drag-drop-zone
 */

import { type FC, useState, useRef, useCallback } from 'react'
import { cn } from '@/lib/utils'
import Icon from './icon'

/**
 * Props for the DragDropZone component.
 */
export interface DragDropZoneProps {
  /**
   * Callback fired when valid files are dropped.
   */
  onDrop: (files: File[]) => void
  /**
   * Accepted file extensions (e.g., ['.pdf', '.txt', '.docx'])
   */
  acceptFileTypes: string[]
  /**
   * Maximum file size in megabytes
   */
  maxFileSize: number
  /**
   * Optional additional className
   */
  className?: string
}

/**
 * DragDropZone component for file upload with validation.
 *
 * Features:
 * - Drag and drop support with visual feedback
 * - File picker button as alternative
 * - Client-side file type validation
 * - Client-side file size validation
 * - Touch-friendly on mobile devices
 *
 * @example
 * ```tsx
 * <DragDropZone
 *   onDrop={(files) => console.log('Dropped:', files)}
 *   acceptFileTypes={['.pdf', '.txt', '.docx']}
 *   maxFileSize={50}
 * />
 * ```
 */
const DragDropZone: FC<DragDropZoneProps> = ({
  onDrop,
  acceptFileTypes,
  maxFileSize,
  className
}) => {
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  /**
   * Validates a file against type and size constraints.
   */
  const validateFile = useCallback(
    (file: File): { valid: boolean; error?: string } => {
      // Check file type
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
      if (!acceptFileTypes.includes(fileExtension)) {
        return {
          valid: false,
          error: `Invalid file type. Accepted: ${acceptFileTypes.join(', ')}`
        }
      }

      // Check file size
      const fileSizeMB = file.size / (1024 * 1024)
      if (fileSizeMB > maxFileSize) {
        return {
          valid: false,
          error: `File too large. Maximum size: ${maxFileSize}MB`
        }
      }

      return { valid: true }
    },
    [acceptFileTypes, maxFileSize]
  )

  /**
   * Handles drag over event.
   */
  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])

  /**
   * Handles drag leave event.
   */
  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  /**
   * Handles drop event with file validation.
   */
  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(false)

      const files = Array.from(e.dataTransfer.files)
      const validFiles: File[] = []

      for (const file of files) {
        const validation = validateFile(file)
        if (validation.valid) {
          validFiles.push(file)
        } else {
          console.warn(`File validation failed: ${validation.error}`)
        }
      }

      if (validFiles.length > 0) {
        onDrop(validFiles)
      }
    },
    [onDrop, validateFile]
  )

  /**
   * Handles file picker selection.
   */
  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (!files) return

      const validFiles: File[] = []

      for (const file of Array.from(files)) {
        const validation = validateFile(file)
        if (validation.valid) {
          validFiles.push(file)
        } else {
          console.warn(`File validation failed: ${validation.error}`)
        }
      }

      if (validFiles.length > 0) {
        onDrop(validFiles)
      }

      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    },
    [onDrop, validateFile]
  )

  /**
   * Triggers file picker dialog.
   */
  const handleClick = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload files"
      className={cn(
        'flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-all duration-200',
        'hover:border-primary/50 hover:bg-primary/5',
        'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
        isDragging ? 'border-primary bg-primary/10' : 'border-border',
        className
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          handleClick()
        }
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept={acceptFileTypes.join(',')}
        multiple
        onChange={handleFileSelect}
        aria-hidden="true"
      />

      <Icon
        type="upload"
        size="lg"
        className={cn(
          'mb-4 transition-transform duration-200',
          isDragging ? 'scale-110' : ''
        )}
      />

      <p className="text-foreground text-sm font-medium">
        {isDragging ? 'Drop your files here' : 'Drag & drop files here'}
      </p>

      <p className="text-muted-foreground mt-2 text-xs">or click to browse</p>

      <p className="text-muted-foreground mt-4 text-xs">
        Accepted: {acceptFileTypes.join(', ')} • Max {maxFileSize}MB
      </p>
    </div>
  )
}

export default DragDropZone
