"""
Simple document search tool that directly queries ChromaDB.

This bypasses Agno's Knowledge class and directly uses the existing
ChromaDB collection that has the uploaded documents.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from case_chat.config import get_app_settings
from case_chat.embeddings.local_embedder import LocalEmbedder

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DocumentSearchTool:
    """Simple document search tool that queries existing ChromaDB collection."""

    __slots__ = ("embedder",)

    def __init__(self):
        """Initialize the document search tool."""
        self.embedder = LocalEmbedder()
        logger.info("[RAG] DocumentSearchTool initialized with local embedder")

    def search_documents(self, query: str) -> str:
        """
        Search documents for relevant information.

        Args:
            query: The search query

        Returns:
            Formatted results from the documents

        """
        try:
            import chromadb

            settings = get_app_settings()
            client = chromadb.PersistentClient(path=settings.chroma_db_path)
            collection = client.get_collection("case_chat_documents")

            # Generate query embedding
            query_embedding = self.embedder.embed_text(query)

            # Search ChromaDB
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=5,
                include=["documents", "metadatas", "distances"],
            )

            if not results or not results["documents"] or not results["documents"][0]:
                return "No relevant documents found for your query."

            # Format results
            formatted = []
            formatted.append("Based on the uploaded documents:\n")

            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
                strict=False,
            ):
                filename = meta.get("filename", "Unknown")
                score = 1 - dist  # Convert distance to similarity score

                formatted.append(f"[Document: {filename}] (Relevance: {score:.2f})\n\n{doc}\n")

            return "\n".join(formatted)

        except Exception as e:
            logger.error(f"[RAG] Error searching documents: {e}")
            return f"Error searching documents: {str(e)}"


def create_document_search_function():
    """
    Create a simple document search function for Agno.

    Returns a function that can be registered as a tool.
    """
    search_tool = DocumentSearchTool()

    def search_documents(query: str) -> str:
        """
        Search uploaded documents for relevant information.

        Args:
            query: Your question about the documents

        Returns:
            Relevant document excerpts with citations

        """
        return search_tool.search_documents(query)

    return search_documents
