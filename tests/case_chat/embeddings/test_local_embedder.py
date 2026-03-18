"""
Tests for local embedding service.

Tests embedding generation using sentence-transformers (100% local).
"""

from __future__ import annotations

import pytest

from case_chat.embeddings.local_embedder import LocalEmbedder

# ============================================================================
# LocalEmbedder Tests
# ============================================================================


class TestLocalEmbedder:
    """Test local embedding functionality."""

    def test_embedder_initialization(self):
        """Test embedder initializes correctly with default model."""
        embedder = LocalEmbedder()

        assert embedder is not None
        assert embedder._model is not None
        assert embedder.embedding_dimension > 0

    def test_embed_text(self):
        """Test embedding a single text."""
        embedder = LocalEmbedder()

        # Test embedding
        embedding = embedder.embed_text("test text")

        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    def test_embed_batch(self):
        """Test embedding multiple texts."""
        embedder = LocalEmbedder()

        # Test batch embedding
        texts = ["text 1", "text 2", "text 3"]
        embeddings = embedder.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(isinstance(emb, list) for emb in embeddings)
        assert all(len(emb) == embedder.embedding_dimension for emb in embeddings)

    def test_embed_empty_text_raises_error(self):
        """Test that empty text raises ValueError."""
        embedder = LocalEmbedder()

        with pytest.raises(ValueError, match="Text cannot be empty"):
            embedder.embed_text("")

    def test_embed_empty_list_raises_error(self):
        """Test that empty list raises ValueError."""
        embedder = LocalEmbedder()

        with pytest.raises(ValueError, match="Texts list cannot be empty"):
            embedder.embed_batch([])

    def test_embed_all_empty_texts_raises_error(self):
        """Test that list with only empty texts raises ValueError."""
        embedder = LocalEmbedder()

        with pytest.raises(ValueError, match="No valid texts provided"):
            embedder.embed_batch(["", "  ", "\t"])

    def test_embedding_dimension_consistency(self):
        """Test that embedding dimension is consistent."""
        embedder = LocalEmbedder()

        embeddings = embedder.embed_batch(["test 1", "test 2", "test 3"])

        dimensions = [len(emb) for emb in embeddings]
        assert len(set(dimensions)) == 1  # All dimensions are the same
        assert dimensions[0] == embedder.embedding_dimension

    def test_multilingual_support(self):
        """Test that embedder works with Chinese and English text."""
        embedder = LocalEmbedder()

        # Test English
        embedding_en = embedder.embed_text("This is a test in English.")

        # Test Chinese
        embedding_zh = embedder.embed_text("这是一个中文测试。")

        # Both should work
        assert len(embedding_en) > 0
        assert len(embedding_zh) > 0
        assert len(embedding_en) == len(embedding_zh)  # Same dimension
