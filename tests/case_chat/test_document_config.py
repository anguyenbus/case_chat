"""
Tests for document upload and RAG configuration.

Tests configuration loading for ChromaDB path, chunking parameters,
file size limits, and allowed file types.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from case_chat.config import AppSettings, _reset_config_cache, get_app_settings

# ============================================================================
# Test Constants
# ============================================================================

DEFAULT_CHROMA_PATH: Final[Path] = Path("data/chroma")
DEFAULT_DOCUMENTS_PATH: Final[Path] = Path("data/documents")
DEFAULT_MAX_FILE_SIZE_MB: Final[int] = 50
DEFAULT_CHUNK_SIZE_TOKENS: Final[int] = 750
DEFAULT_CHUNK_OVERLAP_PCT: Final[int] = 10
DEFAULT_ALLOWED_TYPES: Final[list[str]] = [".pdf", ".txt", ".docx"]


# ============================================================================
# Configuration Tests
# ============================================================================


class TestDocumentConfig:
    """Test document-related configuration settings."""

    def setup_method(self):
        """Reset configuration cache before each test."""
        _reset_config_cache()

    def test_default_chroma_db_path(self):
        """Test default ChromaDB path configuration."""
        settings = AppSettings()
        assert hasattr(settings, "chroma_db_path")
        assert settings.chroma_db_path == DEFAULT_CHROMA_PATH

    def test_default_documents_path(self):
        """Test default documents storage path configuration."""
        settings = AppSettings()
        assert hasattr(settings, "documents_path")
        assert settings.documents_path == DEFAULT_DOCUMENTS_PATH

    def test_default_max_file_size_mb(self):
        """Test default maximum file size limit (50MB)."""
        settings = AppSettings()
        assert hasattr(settings, "max_file_size_mb")
        assert settings.max_file_size_mb == DEFAULT_MAX_FILE_SIZE_MB

    def test_default_chunk_size_tokens(self):
        """Test default chunk size in tokens (750)."""
        settings = AppSettings()
        assert hasattr(settings, "chunk_size_tokens")
        assert settings.chunk_size_tokens == DEFAULT_CHUNK_SIZE_TOKENS

    def test_default_chunk_overlap_pct(self):
        """Test default chunk overlap percentage (10%)."""
        settings = AppSettings()
        assert hasattr(settings, "chunk_overlap_pct")
        assert settings.chunk_overlap_pct == DEFAULT_CHUNK_OVERLAP_PCT

    def test_default_allowed_file_types(self):
        """Test default allowed file types (.pdf, .txt, .docx)."""
        settings = AppSettings()
        assert hasattr(settings, "allowed_file_types")
        assert settings.allowed_file_types == DEFAULT_ALLOWED_TYPES

    def test_custom_max_file_size_via_env(self):
        """Test custom file size limit via environment variable."""
        os.environ["CASE_CHAT_MAX_FILE_SIZE_MB"] = "100"
        _reset_config_cache()

        settings = AppSettings()
        assert settings.max_file_size_mb == 100

        # Cleanup
        del os.environ["CASE_CHAT_MAX_FILE_SIZE_MB"]

    def test_custom_chunk_size_via_env(self):
        """Test custom chunk size via environment variable."""
        os.environ["CASE_CHAT_CHUNK_SIZE_TOKENS"] = "1000"
        _reset_config_cache()

        settings = AppSettings()
        assert settings.chunk_size_tokens == 1000

        # Cleanup
        del os.environ["CASE_CHAT_CHUNK_SIZE_TOKENS"]

    def test_get_app_settings_returns_singleton(self):
        """Test that get_app_settings returns cached instance."""
        settings1 = get_app_settings()
        settings2 = get_app_settings()
        assert settings1 is settings2

    def test_data_directory_creation(self):
        """Test that data directories can be created."""
        import shutil

        settings = get_app_settings()

        # Create test directories
        test_chroma = settings.chroma_db_path / "test"
        test_docs = settings.documents_path / "test"

        test_chroma.mkdir(parents=True, exist_ok=True)
        test_docs.mkdir(parents=True, exist_ok=True)

        # Verify they exist
        assert test_chroma.exists()
        assert test_docs.exists()

        # Cleanup
        if test_chroma.exists():
            shutil.rmtree(test_chroma)
        if test_docs.exists():
            shutil.rmtree(test_docs)
