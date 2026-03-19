"""
Local embedding service.

Generates embeddings using sentence-transformers (100% local).
Implements Agno's Embedder interface for compatibility with KnowledgeTools.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Final

from agno.knowledge.embedder.base import Embedder

logger = logging.getLogger(__name__)


# ============================================================================
# Local Embedder
# ============================================================================


class LocalEmbedder(Embedder):
    """
    Generate embeddings using sentence-transformers (100% local).

    Uses pre-trained sentence-transformer models to generate vector
    embeddings for text chunks. No API calls required - everything
    runs locally. Implements Agno's Embedder interface for use with
    KnowledgeTools and RAG.

    Attributes
    ----------
    dimensions : int
        Dimension of the embedding vectors (set by Embedder base class)
    enable_batch : bool
        Whether batch embedding is enabled
    batch_size : int
        Number of texts to process in each batch
    _model_name : str
        Name of the sentence-transformer model
    _model : SentenceTransformer
        Loaded sentence-transformer model

    """

    __slots__ = ("_model_name", "_model")

    # Recommended models for Chinese and English
    DEFAULT_MODEL: Final[str] = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    ALTERNATIVE_MODEL: Final[str] = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(
        self,
        model_name: str | None = None,
        cache_dir: str | Path | None = None,
    ):
        """
        Initialize the LocalEmbedder.

        Parameters
        ----------
        model_name : Optional[str]
            Name of the sentence-transformer model.
            Defaults to multilingual model supporting Chinese and English.
        cache_dir : Optional[str | Path]
            Directory to cache downloaded models.
            Defaults to ~/.cache/torch/sentence_transformers/

        Raises
        ------
        ImportError
            If sentence-transformers is not installed

        Examples
        --------
        >>> embedder = LocalEmbedder()
        >>> embedding = embedder.get_embedding("Hello world")

        """
        self._model_name = model_name or self.DEFAULT_MODEL

        # Set cache directory for models
        cache_dir = str(cache_dir) if cache_dir else None

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading local embedding model: {self._model_name}")

            self._model = SentenceTransformer(
                self._model_name,
                cache_folder=cache_dir,
                device="cpu",  # Force CPU to avoid CUDA compatibility issues
            )

            # Get embedding dimension and set it for Embedder base class
            self.dimensions = self._model.get_sentence_embedding_dimension()
            # Enable batch processing for better performance
            self.enable_batch = True

            logger.info(f"Loaded local embedder: {self._model_name} (dimension={self.dimensions})")

        except ImportError as e:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Install it with: uv add sentence-transformers"
            ) from e

    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Parameters
        ----------
        text : str
            Text to embed

        Returns
        -------
        list[float]
            Embedding vector

        Raises
        ------
        ValueError
            If text is empty

        Examples
        --------
        >>> embedder = LocalEmbedder()
        >>> embedding = embedder.embed_text("Hello world")

        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        embeddings = self.embed_batch([text])
        return embeddings[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Parameters
        ----------
        texts : list[str]
            List of texts to embed

        Returns
        -------
        list[list[float]]
            List of embedding vectors

        Raises
        ------
        ValueError
            If texts list is empty

        Examples
        --------
        >>> embedder = LocalEmbedder()
        >>> embeddings = embedder.embed_batch(["text 1", "text 2"])

        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        # Filter out empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            raise ValueError("No valid texts provided")

        logger.debug(f"Generating embeddings for {len(valid_texts)} texts")

        # Generate embeddings using sentence-transformers
        embeddings = self._model.encode(
            valid_texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        # Convert to list of lists
        embedding_list = embeddings.tolist()

        logger.info(f"Generated {len(embedding_list)} embeddings (dim={self.dimensions})")

        return embedding_list

    @property
    def embedding_dimension(self) -> int:
        """
        Get the dimension of embedding vectors.

        Returns
        -------
        int
            Embedding dimension

        """
        return self.dimensions

    # ========================================================================
    # Agno Embedder Interface Implementation
    # ========================================================================

    def get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text (Agno interface).

        This method implements the Agno Embedder interface for use with
        KnowledgeTools and RAG.

        Parameters
        ----------
        text : str
            Text to embed

        Returns
        -------
        list[float]
            Embedding vector

        Raises
        ------
        ValueError
            If text is empty

        Examples
        --------
        >>> embedder = LocalEmbedder()
        >>> embedding = embedder.get_embedding("Hello world")

        """
        return self.embed_text(text)

    def get_embedding_and_usage(self, text: str) -> tuple[list[float], dict | None]:
        """
        Generate embedding for a single text with usage info (Agno interface).

        This method implements the Agno Embedder interface. Since
        sentence-transformers is a local model with no API usage tracking,
        the usage dict is always None.

        Parameters
        ----------
        text : str
            Text to embed

        Returns
        -------
        tuple[list[float], Optional[dict]]
            Embedding vector and None for usage

        Examples
        --------
        >>> embedder = LocalEmbedder()
        >>> embedding, usage = embedder.get_embedding_and_usage("Hello world")
        >>> assert usage is None  # Local model has no usage tracking

        """
        embedding = self.embed_text(text)
        return embedding, None

    async def async_get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding asynchronously (Agno interface).

        This method runs the synchronous embedding in a thread pool
        to provide an async interface for Agno's Knowledge system.

        Parameters
        ----------
        text : str
            Text to embed

        Returns
        -------
        list[float]
            Embedding vector

        Examples
        --------
        >>> embedder = LocalEmbedder()
        >>> embedding = await embedder.async_get_embedding("Hello world")

        """
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            embedding = await loop.run_in_executor(executor, self.embed_text, text)
        return embedding

    async def async_get_embedding_and_usage(self, text: str) -> tuple[list[float], dict | None]:
        """
        Generate embedding asynchronously with usage info (Agno interface).

        This method runs the synchronous embedding in a thread pool
        to provide an async interface for Agno's Knowledge system.
        Since sentence-transformers is a local model with no API usage
        tracking, the usage dict is always None.

        Parameters
        ----------
        text : str
            Text to embed

        Returns
        -------
        tuple[list[float], Optional[dict]]
            Embedding vector and None for usage

        Examples
        --------
        >>> embedder = LocalEmbedder()
        >>> embedding, usage = await embedder.async_get_embedding_and_usage("Hello world")
        >>> assert usage is None  # Local model has no usage tracking

        """
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            embedding = await loop.run_in_executor(executor, self.embed_text, text)
        return embedding, None
