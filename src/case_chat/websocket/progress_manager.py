"""
WebSocket progress manager for real-time updates.

Manages WebSocket connections for document processing progress.
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import uuid4

from fastapi import WebSocket

from case_chat.websocket.models import ProgressMessage

logger = logging.getLogger(__name__)


# ============================================================================
# Progress Manager
# ============================================================================


class ProgressManager:
    """
    Manage WebSocket connections for progress updates.

    Tracks active connections and broadcasts progress messages
    for document processing operations.

    Attributes
    ----------
    _active_connections : dict[str, WebSocket]
        Active WebSocket connections by document_id

    """

    __slots__ = ("_active_connections",)

    def __init__(self):
        """Initialize the ProgressManager."""
        self._active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, document_id: str) -> str:
        """
        Connect a WebSocket client.

        Parameters
        ----------
        websocket : WebSocket
            WebSocket connection
        document_id : str
            Document ID to track

        Returns
        -------
        str
            Connection ID

        """
        connection_id = str(uuid4())

        if document_id not in self._active_connections:
            self._active_connections[document_id] = []

        self._active_connections[document_id].append(websocket)

        logger.info(f"WebSocket connected: {connection_id} for document {document_id}")

        return connection_id

    def disconnect(self, websocket: WebSocket, document_id: str) -> None:
        """
        Disconnect a WebSocket client.

        Parameters
        ----------
        websocket : WebSocket
            WebSocket connection
        document_id : str
            Document ID

        """
        if document_id in self._active_connections:
            try:
                self._active_connections[document_id].remove(websocket)
            except ValueError:
                pass

            if not self._active_connections[document_id]:
                del self._active_connections[document_id]

        logger.debug(f"WebSocket disconnected for document {document_id}")

    async def broadcast_progress(
        self,
        document_id: str,
        stage: str,
        progress_pct: int,
        message: str,
        error: str | None = None,
    ) -> None:
        """
        Broadcast progress update to all connected clients.

        Parameters
        ----------
        document_id : str
            Document ID
        stage : str
            Processing stage (parsing, chunking, embedding, storing, complete, error)
        progress_pct : int
            Progress percentage (0-100)
        message : str
            Progress message
        error : Optional[str]
            Error message if stage is error

        """
        if document_id not in self._active_connections:
            return

        # Create progress message
        progress_msg = ProgressMessage(
            document_id=document_id,
            stage=stage,
            progress_pct=progress_pct,
            message=message,
            timestamp=datetime.utcnow(),
            error=error,
        )

        # Broadcast to all connected clients
        disconnected = []
        for websocket in self._active_connections[document_id]:
            try:
                await websocket.send_json(progress_msg.model_dump())
            except Exception as e:
                logger.warning(f"Failed to send progress: {e}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket, document_id)

        logger.debug(f"Broadcast progress for {document_id}: {stage} ({progress_pct}%)")
