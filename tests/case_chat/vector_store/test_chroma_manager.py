"""
Tests for ChromaDB vector store manager.

Tests ChromaDB initialization, collection operations,
and document CRUD operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import chromadb

from case_chat.vector_store.chroma_manager import ChromaManager

# ============================================================================
# Test Constants
# ============================================================================

TEST_COLLECTION_NAME: Final[str] = "test_case_chat_documents"


# ============================================================================
# ChromaManager Tests
# ============================================================================


class TestChromaManager:
    """Test ChromaDB vector store manager."""

    def setup_method(self):
        """Create a fresh ChromaManager for each test using ephemeral client."""
        # Use ephemeral client for tests to avoid filesystem issues
        self._ephemeral_client = chromadb.EphemeralClient()
        self._test_collection = self._ephemeral_client.get_or_create_collection(
            name=TEST_COLLECTION_NAME,
        )

        # Create manager with a custom client
        self.manager = ChromaManager(
            chroma_path=Path("tmp/test_chroma"),  # Won't be used with our patch
            collection_name=TEST_COLLECTION_NAME,
        )

        # Replace the client and collection with our ephemeral ones
        self.manager._client = self._ephemeral_client
        self.manager._collection = self._test_collection

    def teardown_method(self):
        """Clean up test data."""
        try:
            self._ephemeral_client.delete_collection(name=TEST_COLLECTION_NAME)
        except Exception:
            pass

    def test_chroma_manager_initialization(self):
        """Test ChromaManager initializes correctly."""
        assert self.manager.collection_name == TEST_COLLECTION_NAME
        assert self.manager.collection is not None
        assert self.manager.collection.name == TEST_COLLECTION_NAME

    def test_collection_exists(self):
        """Test that collection is created and accessible."""
        collection = self.manager.get_collection()
        assert collection is not None
        assert collection.name == TEST_COLLECTION_NAME
        assert collection.count() == 0

    def test_add_document(self):
        """Test adding a document to ChromaDB."""
        document_id = "test-doc-1"
        chunks = ["This is chunk 1", "This is chunk 2"]
        metadatas = [
            {"document_id": document_id, "chunk_index": 0, "filename": "test.pdf"},
            {"document_id": document_id, "chunk_index": 1, "filename": "test.pdf"},
        ]

        # Add document
        self.manager.add_document(
            document_id=document_id,
            chunks=chunks,
            metadatas=metadatas,
        )

        # Verify document was added
        collection = self.manager.get_collection()
        assert collection.count() == 2

    def test_search_documents(self):
        """Test searching for similar documents."""
        # Add a document first
        document_id = "test-doc-search"
        chunks = ["The quick brown fox jumps over the lazy dog"]
        metadatas = [{"document_id": document_id, "chunk_index": 0, "filename": "test.pdf"}]

        self.manager.add_document(
            document_id=document_id,
            chunks=chunks,
            metadatas=metadatas,
        )

        # Search for similar content
        results = self.manager.search_documents(query="brown fox", n_results=1)

        assert results is not None
        assert len(results["ids"][0]) > 0
        assert document_id in results["metadatas"][0][0]["document_id"]

    def test_delete_document(self):
        """Test deleting a document from ChromaDB."""
        # Add a document
        document_id = "test-doc-delete"
        chunks = ["Content to delete"]
        metadatas = [{"document_id": document_id, "chunk_index": 0, "filename": "test.pdf"}]

        self.manager.add_document(
            document_id=document_id,
            chunks=chunks,
            metadatas=metadatas,
        )

        # Verify it was added
        collection = self.manager.get_collection()
        assert collection.count() == 1

        # Delete the document
        deleted = self.manager.delete_document(document_id=document_id)
        assert deleted is True

        # Verify it was deleted
        assert collection.count() == 0

    def test_get_document_chunks(self):
        """Test retrieving all chunks for a document."""
        document_id = "test-doc-get"
        chunks = ["Chunk 1", "Chunk 2", "Chunk 3"]
        metadatas = [
            {"document_id": document_id, "chunk_index": 0, "filename": "test.pdf"},
            {"document_id": document_id, "chunk_index": 1, "filename": "test.pdf"},
            {"document_id": document_id, "chunk_index": 2, "filename": "test.pdf"},
        ]

        self.manager.add_document(
            document_id=document_id,
            chunks=chunks,
            metadatas=metadatas,
        )

        # Get document chunks
        results = self.manager.get_document(document_id=document_id)

        assert results is not None
        assert len(results["ids"]) == 3
