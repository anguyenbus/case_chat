"""
Vector store module for document embeddings.

Provides ChromaDB integration for storing and retrieving
document embeddings for RAG functionality.
"""

from case_chat.vector_store.chroma_manager import ChromaManager
from case_chat.vector_store.models import ChunkMetadata, DocumentMetadata, SearchResult

__all__ = [
    "ChromaManager",
    "DocumentMetadata",
    "ChunkMetadata",
    "SearchResult",
]
