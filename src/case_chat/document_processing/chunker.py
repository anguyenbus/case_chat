"""
Text chunker for document processing.

Splits documents into chunks with token limits and overlap.
"""

from __future__ import annotations

import logging
from typing import Final
from uuid import uuid4

from langchain_text_splitters import RecursiveCharacterTextSplitter

from case_chat.vector_store.models import ChunkMetadata

logger = logging.getLogger(__name__)


# ============================================================================
# Text Chunker
# ============================================================================


class TextChunker:
    """
    Split text into chunks with overlap.

    Uses LangChain's RecursiveCharacterTextSplitter to split
    text into chunks of approximately specified token count
    with overlap between consecutive chunks.

    Attributes
    ----------
    _chunk_size : int
        Target chunk size in characters (approximate tokens)
    _chunk_overlap_pct : int
        Overlap percentage (0-100)
    _text_splitter : RecursiveCharacterTextSplitter
        LangChain text splitter instance

    """

    __slots__ = ("_chunk_size", "_chunk_overlap_pct", "_text_splitter")

    DEFAULT_CHUNK_SIZE: Final[int] = 750
    DEFAULT_OVERLAP_PCT: Final[int] = 10

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap_pct: int = DEFAULT_OVERLAP_PCT,
    ):
        """
        Initialize the TextChunker.

        Parameters
        ----------
        chunk_size : int
            Target chunk size in characters (default: 750)
        chunk_overlap_pct : int
            Overlap percentage 0-100 (default: 10)

        Examples
        --------
        >>> chunker = TextChunker(chunk_size=1000, chunk_overlap_pct=15)

        """
        if chunk_size <= 0:
            raise ValueError(f"chunk_size must be positive, got {chunk_size}")

        if not 0 <= chunk_overlap_pct <= 100:
            raise ValueError(f"chunk_overlap_pct must be 0-100, got {chunk_overlap_pct}")

        self._chunk_size = chunk_size
        self._chunk_overlap_pct = chunk_overlap_pct

        # Calculate overlap in characters
        chunk_overlap = int(chunk_size * chunk_overlap_pct / 100)

        # Create text splitter
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk_text(
        self,
        text: str,
        document_id: str,
    ) -> list[ChunkMetadata]:
        """
        Split text into chunks.

        Parameters
        ----------
        text : str
            Text to chunk
        document_id : str
            Parent document ID

        Returns
        -------
        list[ChunkMetadata]
            List of chunk metadata objects

        Examples
        --------
        >>> chunker = TextChunker()
        >>> chunks = chunker.chunk_text("Long text...", document_id="doc-123")

        """
        if not text or not text.strip():
            logger.debug("Empty text provided, returning empty chunks")
            return []

        # Split text
        chunks = self._text_splitter.split_text(text)

        # Create chunk metadata
        chunk_metadata = []
        current_pos = 0

        for i, chunk_text in enumerate(chunks):
            # Find position in original text
            start_pos = text.find(chunk_text, current_pos)
            if start_pos == -1:
                # Fallback if exact match not found
                start_pos = current_pos

            end_pos = start_pos + len(chunk_text)

            # Create chunk metadata
            chunk = ChunkMetadata(
                chunk_id=str(uuid4()),
                document_id=document_id,
                chunk_index=i,
                text=chunk_text,
                start_pos=start_pos,
                end_pos=end_pos,
            )

            chunk_metadata.append(chunk)

            # Update current position
            current_pos = end_pos

        logger.info(f"Chunked text into {len(chunks)} chunks for document {document_id}")

        return chunk_metadata

    @property
    def chunk_size(self) -> int:
        """
        Get the chunk size.

        Returns
        -------
        int
            Target chunk size in characters

        """
        return self._chunk_size

    @property
    def chunk_overlap_pct(self) -> int:
        """
        Get the chunk overlap percentage.

        Returns
        -------
        int
            Overlap percentage (0-100)

        """
        return self._chunk_overlap_pct
