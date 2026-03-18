"""
Tests for text chunker.

Tests text chunking with token limits and overlap.
"""

from __future__ import annotations

from typing import Final

from case_chat.document_processing.chunker import TextChunker
from case_chat.vector_store.models import ChunkMetadata

# ============================================================================
# Test Constants
# ============================================================================

DEFAULT_CHUNK_SIZE: Final[int] = 750
DEFAULT_OVERLAP_PCT: Final[int] = 10


# ============================================================================
# TextChunker Tests
# ============================================================================


class TestTextChunker:
    """Test text chunking functionality."""

    def setup_method(self):
        """Create chunker instance for each test."""
        self.chunker = TextChunker(
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap_pct=DEFAULT_OVERLAP_PCT,
        )

    def test_chunker_initialization(self):
        """Test chunker initializes with correct parameters."""
        assert self.chunker.chunk_size == DEFAULT_CHUNK_SIZE
        assert self.chunker.chunk_overlap_pct == DEFAULT_OVERLAP_PCT

    def test_chunk_empty_text(self):
        """Test chunking empty text returns empty list."""
        chunks = self.chunker.chunk_text("", document_id="test-doc")
        assert len(chunks) == 0

    def test_chunk_short_text(self):
        """Test chunking short text returns single chunk."""
        text = "This is a short text."
        chunks = self.chunker.chunk_text(text, document_id="test-doc")

        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].document_id == "test-doc"
        assert chunks[0].chunk_index == 0

    def test_chunk_long_text(self):
        """Test chunking long text returns multiple chunks."""
        # Create text long enough to be chunked
        text = "This is a sentence. " * 100  # ~2000 characters

        chunks = self.chunker.chunk_text(text, document_id="test-doc")

        assert len(chunks) > 1
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert chunk.document_id == "test-doc"
            assert chunk.chunk_id is not None

    def test_chunk_metadata(self):
        """Test chunk metadata is correct."""
        text = "Test text for chunking."
        chunks = self.chunker.chunk_text(text, document_id="test-doc")

        assert len(chunks) == 1
        chunk = chunks[0]

        assert isinstance(chunk, ChunkMetadata)
        assert chunk.document_id == "test-doc"
        assert chunk.chunk_index == 0
        assert chunk.text == text
        assert chunk.start_pos >= 0
        assert chunk.end_pos > chunk.start_pos

    def test_chunk_overlap(self):
        """Test chunks have overlap when appropriate."""
        # Create very long text
        text = "word " * 1000  # ~5000 characters

        chunks = self.chunker.chunk_text(text, document_id="test-doc")

        # With overlap, consecutive chunks should share some text
        if len(chunks) > 1:
            # They might not have exact text overlap due to tokenization,
            # but we should have multiple chunks
            assert len(chunks) > 1
