"""
WebSocket module for real-time progress updates.

Provides WebSocket connection management for document processing.
"""

from case_chat.websocket.models import ProcessingStage, ProgressMessage
from case_chat.websocket.progress_manager import ProgressManager

__all__ = [
    "ProgressManager",
    "ProgressMessage",
    "ProcessingStage",
]
