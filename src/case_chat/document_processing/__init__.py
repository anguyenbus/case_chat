"""
Document processing module.

Provides document parsing and chunking functionality for RAG.
"""

from case_chat.document_processing.chunker import TextChunker
from case_chat.document_processing.parser import DocumentParser

__all__ = [
    "DocumentParser",
    "TextChunker",
]
