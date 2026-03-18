"""
Document management API endpoints.

Provides FastAPI endpoints for document upload, search, and management.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from case_chat.config import get_app_settings
from case_chat.document_processing.chunker import TextChunker
from case_chat.document_processing.parser import DocumentParser
from case_chat.embeddings import LocalEmbedder
from case_chat.vector_store.chroma_manager import ChromaManager
from case_chat.vector_store.models import DocumentMetadata
from case_chat.websocket.progress_manager import ProgressManager

logger = logging.getLogger(__name__)


# ============================================================================
# API Models
# ============================================================================


class UploadResponse(BaseModel):
    """Response for document upload."""

    document_id: str
    filename: str
    status: str
    message: str


class DocumentListResponse(BaseModel):
    """Response for document list."""

    documents: list[dict[str, Any]]


class SearchRequest(BaseModel):
    """Request for document search."""

    query: str
    top_k: int = 5


class SearchResponse(BaseModel):
    """Response for document search."""

    results: list[dict[str, Any]]
    total_found: int


# ============================================================================
# Router
# ============================================================================

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Global instances
_settings = get_app_settings()
_chroma_manager = ChromaManager(
    chroma_path=_settings.chroma_db_path,
    collection_name="case_chat_documents",
)
_progress_manager = ProgressManager()
_parser = DocumentParser()
_chunker = TextChunker(
    chunk_size=_settings.chunk_size_tokens,
    chunk_overlap_pct=_settings.chunk_overlap_pct,
)
_embedder = LocalEmbedder()  # Local embeddings using sentence-transformers

# In-memory document metadata storage (use proper DB in production)
_document_metadata: dict[str, DocumentMetadata] = {}


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile) -> JSONResponse:
    """
    Upload a document for processing.

    Accepts PDF, TXT, and DOCX files up to 50MB.
    Processes document in background and streams progress via WebSocket.

    Parameters
    ----------
    file : UploadFile
        Uploaded file

    Returns
    -------
    UploadResponse
        Document ID and initial status

    """
    # Validate file type
    try:
        file_ext = _parser.detect_file_type(file.filename or "")
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)},
        )

    # Validate file size
    content = await file.read()
    file_size = len(content)

    if file_size > _settings.max_file_size_mb * 1024 * 1024:
        return JSONResponse(
            status_code=413,
            content={"error": f"File too large. Maximum size is {_settings.max_file_size_mb}MB"},
        )

    # Generate document ID
    document_id = str(uuid4())

    # Save file
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    documents_dir = _settings.documents_path / date_str
    documents_dir.mkdir(parents=True, exist_ok=True)

    file_path = documents_dir / f"{document_id}_{file.filename or 'document'}"

    with open(file_path, "wb") as f:
        f.write(content)

    # Create metadata
    metadata = DocumentMetadata(
        document_id=document_id,
        filename=file.filename or "document",
        file_type=file_ext,
        file_size=file_size,
        status="processing",
    )

    _document_metadata[document_id] = metadata

    # Start background processing
    # For now, process synchronously (use proper background tasks in production)
    try:
        await process_document(document_id, file_path, metadata)
    except Exception as e:
        logger.error(f"Failed to process document {document_id}: {e}")
        metadata.status = "error"
        metadata.error_message = str(e)

        await _progress_manager.broadcast_progress(
            document_id=document_id,
            stage="error",
            progress_pct=0,
            message="Processing failed",
            error=str(e),
        )

    return JSONResponse(
        content=UploadResponse(
            document_id=document_id,
            filename=file.filename or "document",
            status=metadata.status,
            message="Document uploaded successfully",
        ).model_dump(),
    )


async def process_document(
    document_id: str,
    file_path: Path,
    metadata: DocumentMetadata,
) -> None:
    """
    Process a document: parse, chunk, and embed.

    Parameters
    ----------
    document_id : str
        Document ID
    file_path : Path
        Path to document file
    metadata : DocumentMetadata
        Document metadata to update

    """
    # Parse document
    await _progress_manager.broadcast_progress(
        document_id=document_id,
        stage="parsing",
        progress_pct=25,
        message="Parsing document...",
    )

    if metadata.file_type == ".pdf":
        text, _ = _parser.parse_pdf(file_path)
    elif metadata.file_type == ".txt":
        text, _ = _parser.parse_txt(file_path)
    elif metadata.file_type == ".docx":
        text, _ = _parser.parse_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {metadata.file_type}")

    # Chunk document
    await _progress_manager.broadcast_progress(
        document_id=document_id,
        stage="chunking",
        progress_pct=50,
        message="Chunking document...",
    )

    chunks = _chunker.chunk_text(text, document_id)

    # Generate embeddings and store in ChromaDB
    await _progress_manager.broadcast_progress(
        document_id=document_id,
        stage="embedding",
        progress_pct=75,
        message="Generating embeddings...",
    )

    # Generate embeddings for all chunks
    chunk_texts = [chunk.text for chunk in chunks]
    logger.info(f"[EMBED] Generating embeddings for {len(chunk_texts)} chunks")

    try:
        embeddings = _embedder.embed_batch(chunk_texts)
        logger.info(f"[EMBED] Generated {len(embeddings)} embeddings")

        # Store chunks with embeddings in ChromaDB
        await _progress_manager.broadcast_progress(
            document_id=document_id,
            stage="storing",
            progress_pct=90,
            message="Storing in vector database...",
        )

        _chroma_manager.add_chunks_with_embeddings(
            document_id=document_id,
            filename=metadata.filename,
            chunks=chunks,
            embeddings=embeddings,
        )

        logger.info(f"[CHROMA] Stored {len(chunks)} chunks in ChromaDB")

    except Exception as e:
        logger.error(f"[EMBED] Failed to generate embeddings: {e}")
        raise

    await _progress_manager.broadcast_progress(
        document_id=document_id,
        stage="storing",
        progress_pct=100,
        message="Document processed successfully",
    )

    # Update metadata
    metadata.chunk_count = len(chunks)
    metadata.status = "ready"


@router.get("", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    """
    List all documents.

    Returns
    -------
    DocumentListResponse
        List of document metadata

    """
    documents = [
        {
            "document_id": doc_id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "upload_timestamp": doc.upload_timestamp.isoformat(),
            "chunk_count": doc.chunk_count,
            "status": doc.status,
            "error_message": doc.error_message,
        }
        for doc_id, doc in _document_metadata.items()
    ]

    return DocumentListResponse(documents=documents)


@router.get("/{document_id}")
async def get_document(document_id: str) -> JSONResponse:
    """
    Get document details.

    Parameters
    ----------
    document_id : str
        Document ID

    Returns
    -------
    JSONResponse
        Document metadata

    """
    if document_id not in _document_metadata:
        return JSONResponse(
            status_code=404,
            content={"error": "Document not found"},
        )

    doc = _document_metadata[document_id]

    return JSONResponse(
        content={
            "document_id": doc.document_id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "upload_timestamp": doc.upload_timestamp.isoformat(),
            "chunk_count": doc.chunk_count,
            "status": doc.status,
            "error_message": doc.error_message,
        },
    )


@router.delete("/{document_id}")
async def delete_document(document_id: str) -> JSONResponse:
    """
    Delete a document.

    Parameters
    ----------
    document_id : str
        Document ID

    Returns
    -------
    JSONResponse
        Deletion status

    """
    if document_id not in _document_metadata:
        return JSONResponse(
            status_code=404,
            content={"error": "Document not found"},
        )

    # Delete from ChromaDB
    _chroma_manager.delete_document(document_id)

    # Delete from metadata
    del _document_metadata[document_id]

    return JSONResponse(
        content={
            "status": "success",
            "message": "Document deleted successfully",
        },
    )


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest) -> SearchResponse:
    """
    Search documents by semantic similarity.

    Parameters
    ----------
    request : SearchRequest
        Search query and parameters

    Returns
    -------
    SearchResponse
        Search results

    """
    results = _chroma_manager.search_documents(
        query=request.query,
        n_results=request.top_k,
    )

    if results is None:
        return SearchResponse(results=[], total_found=0)

    # Format results
    formatted_results = []
    for i, doc_id in enumerate(results.get("ids", [[]])[0]):
        formatted_results.append(
            {
                "chunk_id": doc_id,
                "document_id": results["metadatas"][0][i].get("document_id", ""),
                "text": results["documents"][0][i],
                "relevance_score": 1.0 - results.get("distances", [[]])[0][i]
                if results.get("distances")
                else 0.0,
            }
        )

    return SearchResponse(results=formatted_results, total_found=len(formatted_results))


@router.websocket("/progress")
async def document_progress(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for document processing progress.

    Query Parameters
    ---------------
    document_id : str
        Document ID to track

    """
    await websocket.accept()

    # Get document_id from query params
    document_id = websocket.query_params.get("document_id", "")

    if not document_id:
        await websocket.close(code=1008, reason="Missing document_id")
        return

    # Connect to progress manager
    connection_id = await _progress_manager.connect(websocket, document_id)

    try:
        # Keep connection alive
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        _progress_manager.disconnect(websocket, document_id)
        logger.info(f"WebSocket disconnected: {connection_id}")
