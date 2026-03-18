"""
Data models for document and chunk metadata.

Defines Pydantic models for document metadata and chunk information
stored in the vector store and metadata database.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final
from uuid import uuid4

from pydantic import BaseModel, Field

# ============================================================================
# Document Metadata Models
# ============================================================================


class DocumentMetadata(BaseModel):
    """
    Metadata for an uploaded document.

    Attributes
    ----------
    document_id : str
        Unique identifier for the document (UUID)
    filename : str
        Original filename of the uploaded file
    file_type : str
        File extension (e.g., '.pdf', '.txt', '.docx')
    file_size : int
        File size in bytes
    upload_timestamp : datetime
        When the document was uploaded
    chunk_count : int
        Number of chunks the document was split into
    status : str
        Processing status: 'processing', 'ready', 'error'
    error_message : str | None
        Error message if status is 'error'

    """

    document_id: str = Field(default_factory=lambda: str(uuid4()))
    filename: str
    file_type: str
    file_size: int
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    chunk_count: int = 0
    status: str = Field(default="processing")
    error_message: str | None = None


# ============================================================================
# Chunk Metadata Models
# ============================================================================


class ChunkMetadata(BaseModel):
    """
    Metadata for a text chunk.

    Attributes
    ----------
    chunk_id : str
        Unique identifier for the chunk
    document_id : str
        Parent document ID
    chunk_index : int
        Sequential index of the chunk in the document
    text : str
        The chunk text content
    start_pos : int
        Starting character position in the original document
    end_pos : int
        Ending character position in the original document

    """

    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    chunk_index: int
    text: str
    start_pos: int
    end_pos: int


# ============================================================================
# Search Result Models
# ============================================================================


class SearchResult(BaseModel):
    """
    Result from a vector similarity search.

    Attributes
    ----------
    chunk_id : str
        Unique identifier for the chunk
    document_id : str
        Parent document ID
    document_name : str
        Filename of the source document
    chunk_index : int
        Index of the chunk in the document
    text : str
        The chunk text content
    relevance_score : float
        Similarity score (0-1, higher is more relevant)
    metadata : dict
        Additional metadata from the vector store

    """

    chunk_id: str
    document_id: str
    document_name: str
    chunk_index: int
    text: str
    relevance_score: float
    metadata: dict


# ============================================================================
# Type Constants
# ============================================================================

DocumentStatus: Final[dict[str, str]] = {
    "PROCESSING": "processing",
    "READY": "ready",
    "ERROR": "error",
}
