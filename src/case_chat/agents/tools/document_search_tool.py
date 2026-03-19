"""
Document search tool for RAG.

This module provides an Agno tool for searching uploaded documents
and returning relevant chunks with citations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agno.tools import Toolkit

from case_chat.config import get_app_settings
from case_chat.embeddings.glm5_embedder import GLM5Embedder
from case_chat.vector_store.chroma_manager import ChromaManager

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DocumentSearchTool:
    """
    Tool for searching uploaded documents using RAG.

    This tool searches the ChromaDB vector store for relevant
    document chunks based on the user's question.

    Attributes
    ----------
    chroma_manager : ChromaManager
        The ChromaDB manager for document search
    embedder : GLM5Embedder
        The embedder for query embedding

    """

    __slots__ = ("chroma_manager", "embedder", "top_k")

    def __init__(self, top_k: int = 5):
        """
        Initialize the DocumentSearchTool.

        Parameters
        ----------
        top_k : int
            Number of relevant chunks to retrieve (default: 5)

        """
        settings = get_app_settings()

        # Initialize ChromaDB manager
        self.chroma_manager = ChromaManager(
            persist_path=settings.chroma_db_path, collection_name="case_chat_documents"
        )

        # Initialize embedder
        self.embedder = GLM5Embedder(api_key=settings.z_api_key, model="embedding-3")

        self.top_k = top_k

        logger.info(f"[RAG] DocumentSearchTool initialized with top_k={top_k}")

    def search_documents(self, query: str) -> str:
        """
        Search documents for relevant chunks.

        Parameters
        ----------
        query : str
            The search query (user's question)

        Returns
        -------
        str
            Formatted string with relevant document chunks and citations

        Examples
        --------
        >>> tool = DocumentSearchTool()
        >>> result = tool.search_documents("What is the tax rate?")
        >>> print(result)
        Based on the uploaded documents:
        [1] individualupload.pdf (relevance: 0.85)
        The tax rate for...

        """
        if not query or not query.strip():
            return "Please provide a valid search query."

        try:
            # Generate embedding for the query
            query_embedding = self.embedder.embed_text(query)

            # Search ChromaDB
            search_results = self.chroma_manager.search_documents(
                query_embedding=query_embedding, n_results=self.top_k
            )

            if not search_results or len(search_results) == 0:
                return "No relevant documents found. Please upload documents first."

            # Format results
            formatted_results = []
            formatted_results.append("Based on the uploaded documents:\n")

            for idx, result in enumerate(search_results, 1):
                chunk_text = result.get("chunk", "")
                metadata = result.get("metadata", {})
                filename = metadata.get("filename", "Unknown")
                score = result.get("score", 0.0)

                formatted_results.append(
                    f"[{idx}] {filename} (relevance: {score:.2f})\n{chunk_text}\n"
                )

            return "\n".join(formatted_results)

        except Exception as e:
            logger.error(f"[RAG] Error searching documents: {e}")
            return f"Error searching documents: {str(e)}"

    def search_documents_with_references(self, query: str) -> dict:
        """
        Search documents and return structured data for citations.

        This method returns structured data that can be used to generate
        citation links in the frontend.

        Parameters
        ----------
        query : str
            The search query

        Returns
        -------
        dict
            Structured data with results and references for citations

        """
        if not query or not query.strip():
            return {"context": "Please provide a valid search query.", "references": []}

        try:
            # Generate embedding for the query
            query_embedding = self.embedder.embed_text(query)

            # Search ChromaDB
            search_results = self.chroma_manager.search_documents(
                query_embedding=query_embedding, n_results=self.top_k
            )

            if not search_results or len(search_results) == 0:
                return {
                    "context": "No relevant documents found. Please upload documents first.",
                    "references": [],
                }

            # Format context for the agent
            context_chunks = []
            references = []

            for idx, result in enumerate(search_results, 1):
                chunk_text = result.get("chunk", "")
                metadata = result.get("metadata", {})
                filename = metadata.get("filename", "Unknown")
                chunk_id = metadata.get("chunk_id", idx)
                score = result.get("score", 0.0)

                # Add to context
                context_chunks.append(f"[{idx}] {filename}: {chunk_text}")

                # Add to references for citations
                references.append(
                    {
                        "name": filename,
                        "content": chunk_text[:200] + "..."
                        if len(chunk_text) > 200
                        else chunk_text,
                        "meta_data": {"chunk": chunk_id, "score": f"{score:.2f}"},
                    }
                )

            context = "\n\n".join(context_chunks)

            return {"context": context, "references": references}

        except Exception as e:
            logger.error(f"[RAG] Error searching documents: {e}")
            return {"context": f"Error searching documents: {str(e)}", "references": []}


def create_document_search_toolkit() -> Toolkit:
    """
    Create a Toolkit with the document search tool.

    Returns
    -------
    Toolkit
        Toolkit containing the document search tool

    """
    toolkit = Toolkit()
    doc_search = DocumentSearchTool()

    # Register the tool with Agno
    @toolkit.register(
        name="search_documents",
        description="Search uploaded documents for relevant information. "
        "Use this when answering questions that might be related to the uploaded documents.",
    )
    def search_documents(query: str) -> str:
        """
        Search uploaded documents for relevant information.

        Args:
            query: The search query or question

        Returns:
            Relevant document chunks with citations

        """
        return doc_search.search_documents(query)

    logger.info("[RAG] Created document search toolkit")
    return toolkit
