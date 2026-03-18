"""
WebSocket message models.

Defines Pydantic models for WebSocket progress messages.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final

from pydantic import BaseModel, Field

# ============================================================================
# Progress Message Models
# ============================================================================


class ProgressMessage(BaseModel):
    """
    Progress update message for WebSocket clients.

    Attributes
    ----------
    document_id : str
        Document being processed
    stage : str
        Processing stage
    progress_pct : int
        Progress percentage (0-100)
    message : str
        Human-readable progress message
    timestamp : datetime
        When the progress update was sent
    error : str | None
        Error message if stage is 'error'

    """

    document_id: str
    stage: str
    progress_pct: int = Field(ge=0, le=100)
    message: str
    timestamp: datetime
    error: str | None = None


# ============================================================================
# Stage Constants
# ============================================================================

ProcessingStage: Final[dict[str, str]] = {
    "PARSING": "parsing",
    "CHUNKING": "chunking",
    "EMBEDDING": "embedding",
    "STORING": "storing",
    "COMPLETE": "complete",
    "ERROR": "error",
}
