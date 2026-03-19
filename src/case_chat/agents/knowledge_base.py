"""
Knowledge base integration for RAG using Agno's Knowledge system.

This module creates a Knowledge base from the uploaded documents
in ChromaDB and provides KnowledgeTools for the agent.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agno.knowledge.knowledge import Knowledge
from agno.tools.knowledge import KnowledgeTools
from agno.vectordb.chroma import ChromaDb

from case_chat.config import get_app_settings
from case_chat.embeddings.local_embedder import LocalEmbedder

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def create_document_knowledge() -> Knowledge:
    """
    Create a Knowledge base from uploaded documents in ChromaDB.

    Returns
    -------
    Knowledge
        Knowledge base connected to ChromaDB with uploaded documents

    """
    settings = get_app_settings()

    # Create local embedder (100% local, no API calls)
    # Using the same embedder that was used for document upload
    embedder = LocalEmbedder()

    # Create ChromaDB vector database connection
    # Using the same collection name as the document upload feature
    # CRITICAL: persistent_client=True is required to connect to the existing
    # ChromaDB database with uploaded documents. Default (False) creates an
    # ephemeral in-memory database which is empty.
    # NOTE: Settings must match the ChromaManager settings to avoid conflicts
    from chromadb.config import Settings as ChromaSettings

    vector_db = ChromaDb(
        collection="case_chat_documents",
        path=settings.chroma_db_path,
        embedder=embedder,
        persistent_client=True,  # Must use persistent client to access existing documents
        # Settings must match ChromaManager to avoid "already exists with different settings" error
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True,
        ),
    )

    # CRITICAL: Initialize the collection explicitly
    # Knowledge.__post_init__ only calls vector_db.create() if not exists(),
    # but we need to call it regardless to initialize _collection attribute.
    vector_db.create()
    logger.info(
        f"[RAG] Initialized ChromaDB collection with {vector_db._collection.count()} documents"
    )

    # Create Knowledge base
    # Note: isolate_vector_search=False is required because the existing
    # documents in ChromaDB don't have 'linked_to' metadata. Setting this
    # to False allows all documents in the collection to be searched.
    knowledge = Knowledge(
        vector_db=vector_db,
        name="case_chat_documents",
        isolate_vector_search=False,  # Don't filter by linked_to metadata
    )

    logger.info("[RAG] Created Knowledge base from ChromaDB")
    logger.info("[RAG] Collection: case_chat_documents")
    logger.info(f"[RAG] Persist path: {settings.chroma_db_path}")

    return knowledge


def create_knowledge_tools() -> KnowledgeTools:
    """
    Create KnowledgeTools for the agent.

    Returns
    -------
    KnowledgeTools
        KnowledgeTools configured for document search and analysis

    """
    knowledge = create_document_knowledge()

    tools = KnowledgeTools(
        knowledge=knowledge,
        # Enable all knowledge tools
        enable_think=True,  # Enable reasoning before search
        enable_search=True,  # Enable document search
        enable_analyze=True,  # Enable document analysis
        # Add instructions to help the agent use the tools effectively
        add_instructions=True,
        add_few_shot=True,
    )

    logger.info("[RAG] Created KnowledgeTools with search, analyze, and think capabilities")

    return tools
