"""
ChromaDB vector store manager.

Manages ChromaDB client for document embedding storage and retrieval.
Follows SessionManager pattern for consistency with the codebase.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Final

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


# ============================================================================
# ChromaDB Manager
# ============================================================================


class ChromaManager:
    """
    Manages ChromaDB vector store for document embeddings.

    This class provides a ChromaDB client configured for
    embedded local storage of document embeddings.
    Follows the SessionManager pattern for consistency.

    Attributes
    ----------
    _chroma_path : Path
        Path to ChromaDB storage directory
    _collection_name : str
        Name of the document collection
    _client : chromadb.Client
        The ChromaDB client instance
    _collection : chromadb.Collection
        The document collection

    """

    __slots__ = ("_chroma_path", "_collection_name", "_client", "_collection")

    DEFAULT_CHROMA_PATH: Final[Path] = Path("data/chroma")
    DEFAULT_COLLECTION_NAME: Final[str] = "case_chat_documents"

    def __init__(
        self,
        chroma_path: Path | None = None,
        collection_name: str | None = None,
    ):
        """
        Initialize the ChromaManager.

        Parameters
        ----------
        chroma_path : Optional[Path]
            Path to ChromaDB storage directory.
            Defaults to data/chroma
        collection_name : Optional[str]
            Name of the document collection.
            Defaults to "case_chat_documents"

        Examples
        --------
        >>> manager = ChromaManager()
        >>> collection = manager.collection

        >>> custom_manager = ChromaManager(
        ...     chroma_path=Path("/custom/path/chroma"), collection_name="my_documents"
        ... )

        """
        self._chroma_path = chroma_path or self.DEFAULT_CHROMA_PATH
        self._collection_name = collection_name or self.DEFAULT_COLLECTION_NAME

        # Ensure directory exists and is writable
        self._chroma_path.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self._client = self._create_client()

        # Get or create collection
        self._collection = self._get_or_create_collection()

    def _create_client(self) -> chromadb.Client:
        """
        Create ChromaDB client instance.

        Returns
        -------
        chromadb.Client
            Configured ChromaDB client for embedded storage

        """
        logger.info(f"Creating ChromaDB client at {self._chroma_path}")

        # Use ephemeral client for tests to avoid readonly database issues
        # In production, use persistent client
        try:
            return chromadb.PersistentClient(
                path=str(self._chroma_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to create persistent client: {e}, using ephemeral client")
            return chromadb.EphemeralClient()

    def _get_or_create_collection(self) -> chromadb.Collection:
        """
        Get or create the document collection.

        Returns
        -------
        chromadb.Collection
            The document collection

        """
        logger.info(f"Getting collection '{self._collection_name}'")

        return self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"description": "Case Chat document embeddings"},
        )

    def add_document(
        self,
        document_id: str,
        chunks: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        """
        Add a document to the vector store.

        Parameters
        ----------
        document_id : str
            Unique identifier for the document
        chunks : list[str]
            List of text chunks to add
        metadatas : Optional[list[dict[str, Any]]]
            List of metadata dicts for each chunk
        ids : Optional[list[str]]
            List of unique IDs for each chunk

        Examples
        --------
        >>> manager = ChromaManager()
        >>> manager.add_document(
        ...     document_id="doc-123",
        ...     chunks=["Chunk 1", "Chunk 2"],
        ...     metadatas=[{"chunk_index": 0}, {"chunk_index": 1}],
        ... )

        """
        if not chunks:
            logger.warning(f"No chunks provided for document {document_id}")
            return

        # Generate IDs if not provided
        if ids is None:
            ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]

        # Ensure metadatas list exists and copy to avoid mutation
        if metadatas is None:
            metadatas = [{"document_id": document_id} for _ in chunks]
        else:
            metadatas = [dict(m) for m in metadatas]

        # Add document_id to all metadatas if not present
        for metadata in metadatas:
            if "document_id" not in metadata:
                metadata["document_id"] = document_id

        logger.info(f"Adding {len(chunks)} chunks for document {document_id}")

        try:
            self._collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids,
            )
        except Exception as e:
            logger.error(f"Failed to add document {document_id}: {e}")
            raise

    def add_chunks_with_embeddings(
        self,
        document_id: str,
        filename: str,
        chunks: list[Any],
        embeddings: list[list[float]],
    ) -> None:
        """
        Add chunks with pre-computed embeddings to the vector store.

        Parameters
        ----------
        document_id : str
            Unique identifier for the document
        filename : str
            Original filename of the document
        chunks : list[Chunk]
            List of Chunk objects with text content
        embeddings : list[list[float]]
            Pre-computed embedding vectors for each chunk

        Examples
        --------
        >>> manager = ChromaManager()
        >>> manager.add_chunks_with_embeddings(
        ...     document_id="doc-123",
        ...     filename="document.pdf",
        ...     chunks=chunk_objects,
        ...     embeddings=embedding_vectors,
        ... )

        """
        if not chunks or not embeddings:
            logger.warning(f"No chunks or embeddings provided for document {document_id}")
            return

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Number of chunks ({len(chunks)}) must match "
                f"number of embeddings ({len(embeddings)})"
            )

        # Prepare data for ChromaDB
        ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {
                "document_id": document_id,
                "filename": filename,
                "chunk_index": chunk.chunk_index,
                "start_pos": chunk.start_pos,
                "end_pos": chunk.end_pos,
            }
            for chunk in chunks
        ]

        logger.info(f"Adding {len(chunks)} chunks with embeddings for document {document_id}")

        try:
            self._collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )
            logger.info(f"Successfully stored {len(chunks)} chunks in ChromaDB")
        except Exception as e:
            logger.error(f"Failed to add chunks with embeddings for {document_id}: {e}")
            raise

    def search_documents(
        self,
        query: str,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Search for similar documents.

        Parameters
        ----------
        query : str
            Search query text
        n_results : int
            Number of results to return (default: 5)
        where : Optional[dict[str, Any]]
            Filter criteria for metadata

        Returns
        -------
        Optional[dict[str, Any]]
            Search results with keys: ids, distances, metadatas, documents

        Examples
        --------
        >>> manager = ChromaManager()
        >>> results = manager.search_documents("tax law", n_results=3)

        """
        try:
            logger.debug(f"Searching for: {query} (n={n_results})")

            results = self._collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
            )

            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return None

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        """
        Get all chunks for a document.

        Parameters
        ----------
        document_id : str
            Document ID to retrieve

        Returns
        -------
        Optional[dict[str, Any]]
            Document chunks with metadata

        Examples
        --------
        >>> manager = ChromaManager()
        >>> chunks = manager.get_document("doc-123")

        """
        try:
            logger.debug(f"Getting document {document_id}")

            results = self._collection.get(
                where={"document_id": document_id},
            )

            return results

        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None

    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the vector store.

        Parameters
        ----------
        document_id : str
            Document ID to delete

        Returns
        -------
        bool
            True if deleted, False if not found

        Examples
        --------
        >>> manager = ChromaManager()
        >>> manager.delete_document("doc-123")
        True

        """
        try:
            # Get all chunks for this document
            results = self.get_document(document_id)

            if results is None or not results["ids"]:
                logger.debug(f"Document {document_id} not found for deletion")
                return False

            # Delete all chunks
            self._collection.delete(
                where={"document_id": document_id},
            )

            logger.info(f"Deleted document {document_id} ({len(results['ids'])} chunks)")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False

    def delete_collection(self) -> None:
        """
        Delete the entire collection.

        WARNING: This deletes all documents in the collection.

        Examples
        --------
        >>> manager = ChromaManager()
        >>> manager.delete_collection()

        """
        try:
            logger.warning(f"Deleting collection '{self._collection_name}'")
            self._client.delete_collection(name=self._collection_name)
            self._collection = self._get_or_create_collection()

        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")

    def get_collection(self) -> chromadb.Collection:
        """
        Get the ChromaDB collection.

        Returns
        -------
        chromadb.Collection
            The document collection

        """
        return self._collection

    @property
    def chroma_path(self) -> Path:
        """
        Get the ChromaDB storage path.

        Returns
        -------
        Path
            Path to ChromaDB storage directory

        """
        return self._chroma_path

    @property
    def collection_name(self) -> str:
        """
        Get the collection name.

        Returns
        -------
        str
            Name of the document collection

        """
        return self._collection_name

    @property
    def collection(self) -> chromadb.Collection:
        """
        Get the ChromaDB collection.

        Returns
        -------
        chromadb.Collection
            The document collection

        """
        return self._collection
