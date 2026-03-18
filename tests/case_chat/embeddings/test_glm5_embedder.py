"""
Tests for GLM-5 embedding service.

Tests embedding generation for text chunks.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from case_chat.embeddings.glm5_embedder import GLM5Embedder

# ============================================================================
# GLM5Embedder Tests
# ============================================================================


class TestGLM5Embedder:
    """Test GLM-5 embedding functionality."""

    def setup_method(self):
        """Create embedder instance for each test."""
        # Mock the API key for testing
        with patch.dict("os.environ", {"ZHIPUAI_API_KEY": "test-key"}):
            self.embedder = GLM5Embedder()

    def test_embedder_initialization(self):
        """Test embedder initializes correctly."""
        assert self.embedder is not None

    @patch("case_chat.embeddings.glm5_embedder.requests.post")
    def test_embed_text(self, mock_post):
        """Test embedding a single text."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}
        mock_post.return_value = mock_response

        # Test embedding
        embedding = self.embedder.embed_text("test text")

        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    @patch("case_chat.embeddings.glm5_embedder.requests.post")
    def test_embed_batch(self, mock_post):
        """Test embedding multiple texts."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]},
            ]
        }
        mock_post.return_value = mock_response

        # Test batch embedding
        texts = ["text 1", "text 2"]
        embeddings = self.embedder.embed_batch(texts)

        assert len(embeddings) == 2
        assert all(isinstance(emb, list) for emb in embeddings)

    @patch("case_chat.embeddings.glm5_embedder.requests.post")
    def test_error_handling(self, mock_post):
        """Test error handling for API failures."""
        # Mock API error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        # Test error handling
        with pytest.raises(Exception):  # noqa: B017
            self.embedder.embed_text("test text")
