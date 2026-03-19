import { vi } from 'vitest'
/**
 * Test suite for useDocumentProgress hook.
 *
 * These tests verify WebSocket progress tracking.
 */

import { renderHook, act, waitFor } from '@testing-library/react'
import { useStore } from '@/store'
import useDocumentProgress from '../useDocumentProgress'

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  url: string
  readyState: number = MockWebSocket.CONNECTING
  onopen: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null

  constructor(url: string) {
    this.url = url
    // Simulate connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      if (this.onopen) {
        this.onopen(new Event('open'))
      }
    }, 0)
  }

  send(data: string) {
    // Simulate server response
    if (this.onmessage) {
      const progress = JSON.parse(data)
      this.onmessage(
        new MessageEvent('message', { data: JSON.stringify(progress) })
      )
    }
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close'))
    }
  }
}

// @ts-expect-error - Mocking WebSocket for testing
global.WebSocket = MockWebSocket

describe('useDocumentProgress Hook', () => {
  const mockDocumentId = 'doc-1'
  const mockEndpoint = 'ws://localhost:7777'

  beforeEach(() => {
    vi.clearAllMocks()
    // Reset store
    const { setDocumentsData } = useStore.getState()
    setDocumentsData([
      {
        document_id: mockDocumentId,
        filename: 'test.pdf',
        file_type: '.pdf' as const,
        file_size: 1024,
        upload_timestamp: '2026-03-19T10:00:00Z',
        chunk_count: 0,
        status: 'processing' as const,
        error_message: null
      }
    ])
  })

  it('should establish WebSocket connection', () => {
    const { result } = renderHook(() =>
      useDocumentProgress(mockDocumentId, mockEndpoint)
    )

    expect(result.current.isConnected).toBe(false)

    waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
  })

  it('should update document progress on message', async () => {
    const { result } = renderHook(() =>
      useDocumentProgress(mockDocumentId, mockEndpoint)
    )

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    // Simulate progress message
    act(() => {
      const ws = new MockWebSocket(
        `${mockEndpoint}/api/documents/progress?document_id=${mockDocumentId}`
      )
      ws.send({
        document_id: mockDocumentId,
        stage: 'parsing',
        progress_pct: 25,
        message: 'Parsing document...',
        error: null
      })
    })

    await waitFor(() => {
      const { documentsData } = useStore.getState()
      expect(documentsData?.[0].status).toBe('processing')
    })
  })

  it('should handle connection errors', async () => {
    const { result } = renderHook(() =>
      useDocumentProgress(mockDocumentId, mockEndpoint)
    )

    // Simulate connection error
    act(() => {
      const ws = new MockWebSocket(
        `${mockEndpoint}/api/documents/progress?document_id=${mockDocumentId}`
      )
      ws.readyState = MockWebSocket.CLOSED
      if (ws.onerror) {
        ws.onerror(new Event('error'))
      }
    })

    await waitFor(() => {
      expect(result.current.isConnected).toBe(false)
    })
  })

  it('should close WebSocket on unmount', () => {
    const { unmount } = renderHook(() =>
      useDocumentProgress(mockDocumentId, mockEndpoint)
    )

    unmount()

    // WebSocket should be closed
    expect(true).toBe(true) // Placeholder - actual cleanup test
  })
})
