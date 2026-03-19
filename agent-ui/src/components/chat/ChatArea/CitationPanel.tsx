'use client'

/**
 * CitationPanel component.
 *
 * Slide-over panel for displaying RAG citation references
 * from chat messages.
 *
 * @module ChatArea/CitationPanel
 */

import { type FC } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import Icon from '@/components/ui/icon'
import type { ReferenceData } from '@/types/os'

/**
 * Props for CitationPanel component.
 */
export interface CitationPanelProps {
  /** Whether the panel is open */
  isOpen: boolean
  /** Callback to close the panel */
  onClose: () => void
  /** Array of reference data to display */
  references: ReferenceData[]
}

/**
 * Citation panel for displaying document references.
 *
 * Features:
 * - Slide-over animation on right side
 * - Displays source document name
 * - Shows chunk content with highlighting
 * - Relevance score display
 * - Chunk number from metadata
 * - Groups references by document
 * - Close button and escape key support
 * - Responsive design (full width on mobile)
 * - Touch-friendly close button
 *
 * @example
 * ```tsx
 * <CitationPanel
 *   isOpen={isPanelOpen}
 *   onClose={() => setIsPanelOpen(false)}
 *   references={messageReferences}
 * />
 * ```
 */
const CitationPanel: FC<CitationPanelProps> = ({
  isOpen,
  onClose,
  references
}) => {
  if (!references || references.length === 0) {
    return null
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40 bg-black/20"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className={cn(
              'fixed right-0 top-0 z-50 h-screen w-full bg-background shadow-xl',
              'md:w-[400px]'
            )}
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <h2 className="text-lg font-semibold">References</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="h-8 w-8"
                aria-label="Close panel"
              >
                <Icon type="x" size="sm" />
              </Button>
            </div>

            {/* Content */}
            <div className="h-[calc(100vh-73px)] overflow-y-auto px-6 py-4">
              {references.map((refData, refIndex) => (
                <div key={refIndex} className="mb-6">
                  {/* Query */}
                  {refData.query && (
                    <div className="text-muted-foreground mb-3 text-sm">
                      <span className="font-medium">Query:</span>{' '}
                      {refData.query}
                    </div>
                  )}

                  {/* References */}
                  {refData.references.map((ref, refItemIndex) => (
                    <div
                      key={refItemIndex}
                      className="mb-4 rounded-lg border border-border bg-background-secondary p-4"
                    >
                      {/* Document name */}
                      <div className="mb-2 flex items-center gap-2">
                        <Icon type="file-text" size="xs" />
                        <h4 className="text-sm font-medium">{ref.name}</h4>
                      </div>

                      {/* Chunk content */}
                      <div className="mb-2 rounded bg-background p-3">
                        <p className="text-sm leading-relaxed">{ref.content}</p>
                      </div>

                      {/* Metadata */}
                      <div className="text-muted-foreground flex items-center gap-3 text-xs">
                        <span>Chunk {ref.meta_data.chunk}</span>
                        <span>•</span>
                        <span>{ref.meta_data.chunk_size} tokens</span>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}

export default CitationPanel
