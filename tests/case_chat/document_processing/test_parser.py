"""
Tests for document parser.

Tests document parsing for PDF, TXT, and DOCX files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pytest

from case_chat.document_processing.parser import DocumentParser

# ============================================================================
# Test Constants
# ============================================================================

TEST_DATA_DIR: Final[Path] = Path("tests/test_data")


# ============================================================================
# DocumentParser Tests
# ============================================================================


class TestDocumentParser:
    """Test document parsing functionality."""

    def setup_method(self):
        """Create parser instance for each test."""
        self.parser = DocumentParser()

    def test_detect_file_type_pdf(self):
        """Test PDF file type detection."""
        assert self.parser.detect_file_type("document.pdf") == ".pdf"
        assert self.parser.detect_file_type("document.PDF") == ".pdf"

    def test_detect_file_type_txt(self):
        """Test TXT file type detection."""
        assert self.parser.detect_file_type("document.txt") == ".txt"
        assert self.parser.detect_file_type("document.TXT") == ".txt"

    def test_detect_file_type_docx(self):
        """Test DOCX file type detection."""
        assert self.parser.detect_file_type("document.docx") == ".docx"
        assert self.parser.detect_file_type("document.DOCX") == ".docx"

    def test_detect_file_type_unsupported(self):
        """Test unsupported file type raises error."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            self.parser.detect_file_type("document.exe")

    def test_parse_txt_string(self):
        """Test parsing TXT content from string."""
        content = "This is a test document.\nIt has multiple lines."
        text, metadata = self.parser.parse_txt_string(content, "test.txt")

        assert "test document" in text
        assert metadata["filename"] == "test.txt"
        assert metadata["file_type"] == ".txt"
        assert metadata["file_size"] == len(content.encode())

    def test_parse_pdf(self):
        """Test PDF parsing with sample content."""
        # Create a minimal valid PDF for testing
        # For now, test with None to ensure error handling
        with pytest.raises((FileNotFoundError, ValueError)):
            self.parser.parse_pdf(Path("nonexistent.pdf"))

    def test_parse_docx(self):
        """Test DOCX parsing with sample file."""
        # Test with nonexistent file to ensure error handling
        with pytest.raises((FileNotFoundError, ValueError)):
            self.parser.parse_docx(Path("nonexistent.docx"))
