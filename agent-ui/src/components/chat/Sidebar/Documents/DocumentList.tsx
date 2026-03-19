'use client'

/**
 * DocumentList component.
 *
 * Main document list component following the Sessions pattern
 * with accordion-style collapse/expand.
 *
 * @module Documents/DocumentList
 */

import {
  type FC,
  useState,
  useEffect,
  useMemo,
  useRef,
  useCallback
} from 'react'
import { useQueryState } from 'nuqs'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { useStore } from '@/store'
import useDocumentLoader from '@/hooks/useDocumentLoader'
import DocumentItem from './DocumentItem'
import DocumentUploadModal from './DocumentUploadModal'
import DocumentBlankState from './DocumentBlankState'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import Icon from '@/components/ui/icon'
import type { Document } from '@/types/os'

interface SkeletonListProps {
  skeletonCount: number
}

const SkeletonList: FC<SkeletonListProps> = ({ skeletonCount }) => {
  const list = useMemo(
    () => Array.from({ length: skeletonCount }, (_, i) => i),
    [skeletonCount]
  )

  return list.map((k) => (
    <Skeleton
      key={k}
      className="mb-1 h-20 w-full rounded-lg bg-background-secondary"
    />
  ))
}

/**
 * DocumentList component with accordion collapse/expand.
 *
 * Features:
 * - Accordion-style collapse/expand (expanded by default)
 * - Search/filter by filename
 * - Documents shown in default order (newest first)
 * - Document count badge
 * - Upload button
 * - Loading states with skeleton
 * - Blank state when no documents
 * - Custom scrollbar styling
 * - WebSocket progress tracking
 *
 * @example
 * ```tsx
 * <DocumentList />
 * ```
 */
const DocumentList: FC = () => {
  const [agentId] = useQueryState('agent')
  const [teamId] = useQueryState('team')
  const [dbId] = useQueryState('db_id')

  const {
    selectedEndpoint,
    mode,
    isEndpointActive,
    isEndpointLoading,
    hydrated,
    documentsData,
    setDocumentsData,
    isDocumentsLoading
  } = useStore()

  const { getDocuments } = useDocumentLoader()

  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isScrolling, setIsScrolling] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(
    null
  )

  const scrollTimeoutRef = useRef<ReturnType<typeof setTimeout>>(null)

  /**
   * Handles scroll events to show/hide scrollbar.
   */
  const handleScroll = useCallback(() => {
    setIsScrolling(true)

    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current)
    }

    scrollTimeoutRef.current = setTimeout(() => {
      setIsScrolling(false)
    }, 1500)
  }, [])

  /**
   * Cleanup scroll timeout on unmount.
   */
  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current)
      }
    }
  }, [])

  /**
   * Load documents when endpoint or entity changes.
   */
  useEffect(() => {
    if (!selectedEndpoint || isEndpointLoading) return
    if (!(agentId || teamId || dbId)) {
      setDocumentsData([])
      return
    }
    setDocumentsData([])
    getDocuments()
  }, [
    selectedEndpoint,
    agentId,
    teamId,
    dbId,
    mode,
    isEndpointLoading,
    getDocuments,
    setDocumentsData
  ])

  /**
   * Filter documents by search query and sort by date (newest first).
   */
  const filteredDocuments = useMemo(() => {
    if (!documentsData) return []

    let filtered = documentsData

    // Filter by search query
    if (searchQuery) {
      filtered = filtered.filter((doc) =>
        doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    // Sort by date (newest first)
    return filtered.sort((a, b) => {
      return (
        new Date(b.upload_timestamp).getTime() -
        new Date(a.upload_timestamp).getTime()
      )
    })
  }, [documentsData, searchQuery])

  /**
   * Handles document selection.
   */
  const handleDocumentClick = useCallback((document: Document) => {
    setSelectedDocumentId(document.document_id)
  }, [])

  /**
   * Handles document deletion.
   */
  const handleDocumentDelete = useCallback(async (documentId: string) => {
    // Deletion is handled in DocumentItem component
    setSelectedDocumentId(null)
  }, [])

  return (
    <div className="w-full">
      {/* Accordion header */}
      <div
        className="mb-2 flex w-full items-center justify-between"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-medium uppercase">Documents</h2>
          {documentsData && documentsData.length > 0 && (
            <span
              className={cn(
                'flex h-5 items-center rounded-full px-2 text-[10px] font-medium',
                isCollapsed
                  ? 'bg-muted-foreground/20 text-muted-foreground'
                  : 'bg-primary/20 text-primary'
              )}
            >
              {documentsData.length}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={(e) => {
              e.stopPropagation()
              setIsUploadModalOpen(true)
            }}
            aria-label="Upload document"
          >
            <Icon type="upload" size="xs" />
          </Button>

          <motion.div
            animate={{ rotate: isCollapsed ? -90 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <Icon type="chevron-down" size="xs" />
          </motion.div>
        </div>
      </div>

      {/* Accordion content */}
      <AnimatePresence>
        {!isCollapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            {/* Search input */}
            <div className="mb-3">
              <input
                type="text"
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
              />
            </div>

            {/* Document list or blank state */}
            {isDocumentsLoading || isEndpointLoading ? (
              <div className="max-h-[400px] w-full overflow-y-auto">
                <SkeletonList skeletonCount={3} />
              </div>
            ) : !isEndpointActive ||
              (!isDocumentsLoading &&
                (!documentsData || documentsData?.length === 0)) ? (
              <DocumentBlankState onUpload={() => {}} />
            ) : (
              <div
                className={`max-h-[400px] overflow-y-auto font-geist transition-all duration-300 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar]:transition-opacity [&::-webkit-scrollbar]:duration-300 ${
                  isScrolling
                    ? '[&::-webkit-scrollbar-thumb]:rounded-full [&&::-webkit-scrollbar-thumb]:bg-background [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar]:opacity-100'
                    : '[&::-webkit-scrollbar]:opacity-0'
                }`}
                onScroll={handleScroll}
                onMouseOver={() => setIsScrolling(true)}
                onMouseLeave={handleScroll}
              >
                <div className="flex flex-col gap-y-1 pr-1">
                  {filteredDocuments.map((document, idx) => (
                    <DocumentItem
                      key={`${document.document_id}-${idx}`}
                      document={document}
                      onClick={() => handleDocumentClick(document)}
                      onDelete={handleDocumentDelete}
                      isSelected={selectedDocumentId === document.document_id}
                    />
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Upload modal */}
      <DocumentUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        endpoint={selectedEndpoint}
        authToken={useStore.getState().authToken}
      />
    </div>
  )
}

export default DocumentList
