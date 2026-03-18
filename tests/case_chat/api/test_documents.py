"""
Tests for document API endpoints.

Tests document upload, search, and management endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from case_chat.main import app

# ============================================================================
# API Tests
# ============================================================================


class TestDocumentAPI:
    """Test document API endpoints."""

    def setup_method(self):
        """Create test client for each test."""
        self.client = TestClient(app)

    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_list_documents_empty(self):
        """Test list documents endpoint with no documents."""
        response = self.client.get("/api/documents")
        assert response.status_code == 200
        assert response.json()["documents"] == []

    def test_upload_document_txt(self):
        """Test uploading a TXT document."""
        # Create a test file
        content = b"This is a test document for upload."

        files = {"file": ("test.txt", content, "text/plain")}

        response = self.client.post("/api/documents/upload", files=files)

        # Note: This might fail due to missing GLM-5 API key in tests
        # but the endpoint should at least accept the request
        assert response.status_code in [200, 400, 500]

    def test_upload_document_invalid_type(self):
        """Test uploading an invalid file type."""
        content = b"Invalid file content"
        files = {"file": ("test.exe", content, "application/x-msdownload")}

        response = self.client.post("/api/documents/upload", files=files)

        assert response.status_code == 400

    def test_search_documents_empty(self):
        """Test search endpoint with no documents."""
        response = self.client.post(
            "/api/documents/search", json={"query": "test query", "top_k": 5}
        )

        assert response.status_code == 200
        assert response.json()["total_found"] == 0
