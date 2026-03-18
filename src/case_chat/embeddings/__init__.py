"""
Embeddings module for local document chunk embeddings.

Provides 100% local embedding generation using sentence-transformers.
"""

from case_chat.embeddings.local_embedder import LocalEmbedder

__all__ = [
    "LocalEmbedder",
]
