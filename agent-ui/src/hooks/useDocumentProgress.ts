/**
 * useDocumentProgress hook.
 *
 * Custom hook for WebSocket-based document processing progress tracking.
 *
 * @module hooks/useDocumentProgress
 */

import { useEffect, useState, useRef, useCallback } from 'react'
import { useStore } from '@/store'
import type { ProcessingProgress } from '@/types/os'

/**
 * Custom hook for tracking document processing progress via WebSocket.
 *
 * Features:
 * - Establishes WebSocket connection for progress updates
 * - Updates document in store with progress data
 * - Handles connection status changes
 * - Automatic reconnection on disconnect
 * - Cleanup on unmount
 *
 * @param documentId - Document ID to track
 * @param endpoint - WebSocket endpoint URL (ws:// or wss://)
 * @returns Object containing connection status and progress data
 *
 * @example
 * ```tsx
 * const { isConnected, progress } = useDocumentProgress(
 *   'doc-123',
 *   'ws://localhost:7777'
 * )
 * ```
 */
const useDocumentProgress = (documentId: string, endpoint: string) => {
  const [isConnected, setIsConnected] = useState(false)
  const [progress, setProgress] = useState<ProcessingProgress | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const MAX_RECONNECT_ATTEMPTS = 5

  const { documentsData, setDocumentsData } = useStore()

  /**
   * Updates document in store with progress data.
   */
  const updateDocumentProgress = useCallback(
    (progressData: ProcessingProgress) => {
      setProgress(progressData)

      // Update document in store
      if (documentsData) {
        setDocumentsData((prev) =>
          prev?.map((doc) => {
            if (doc.document_id === progressData.document_id) {
              return {
                ...doc,
                status:
                  progressData.stage === 'complete'
                    ? 'ready'
                    : progressData.stage === 'error'
                      ? 'error'
                      : 'processing',
                error_message: progressData.error
              }
            }
            return doc
          })
        )
      }
    },
    [documentsData, setDocumentsData]
  )

  /**
   * Connects to WebSocket for progress updates.
   */
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      const wsUrl = `${endpoint}/api/documents/progress?document_id=${documentId}`
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('[WS_PROGRESS] Connected to progress stream:', documentId)
        setIsConnected(true)
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const progressData: ProcessingProgress = JSON.parse(event.data)
          updateDocumentProgress(progressData)
        } catch (error) {
          console.error('[WS_PROGRESS] Failed to parse message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('[WS_PROGRESS] WebSocket error:', error)
        setIsConnected(false)
      }

      ws.onclose = () => {
        console.log('[WS_PROGRESS] Connection closed:', documentId)
        setIsConnected(false)

        // Attempt reconnection if not manually closed
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++
            console.log(
              `[WS_PROGRESS] Reconnecting... Attempt ${reconnectAttemptsRef.current}`
            )
            connect()
          }, 2000 * reconnectAttemptsRef.current) // Exponential backoff
        }
      }

      wsRef.current = ws
    } catch (error) {
      console.error('[WS_PROGRESS] Failed to connect:', error)
      setIsConnected(false)
    }
  }, [documentId, endpoint, updateDocumentProgress])

  /**
   * Disconnects WebSocket connection.
   */
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setIsConnected(false)
  }, [])

  /**
   * Connect on mount and disconnect on unmount.
   */
  useEffect(() => {
    if (documentId && endpoint) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [documentId, endpoint, connect, disconnect])

  return {
    isConnected,
    progress
  }
}

export default useDocumentProgress
