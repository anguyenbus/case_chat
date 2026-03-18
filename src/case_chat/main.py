"""
Case Chat - Main Application.

FastAPI application serving the Case Chat API.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from case_chat.api.documents import router as documents_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Application metadata
APP_NAME = "Case Chat"
APP_VERSION = "0.1.0"

# Create FastAPI application
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Tax Law Case Analysis with AI Agents",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# ============================================================================
# Include Routers
# ============================================================================

app.include_router(documents_router)


# ============================================================================
# Health Check Endpoints
# ============================================================================


@app.get("/ping")
async def ping() -> dict[str, str]:
    """
    Ping endpoint for health checks.

    Returns a simple status response. Used by load balancers
    and monitoring systems to verify service availability.

    Returns
    -------
    dict
        Status indicator

    """
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict[str, str]:
    """
    Health check endpoint with detailed status.

    Provides information about the application state and
    connected services. Used for monitoring and diagnostics.

    Returns
    -------
    dict
        Health status information

    """
    return {
        "status": "healthy",
        "service": APP_NAME,
        "version": APP_VERSION,
    }


# ============================================================================
# API Root
# ============================================================================


@app.get("/")
async def root() -> dict[str, str]:
    """
    Get API root information.

    Returns basic API information and available endpoints.

    Returns
    -------
    dict
        API metadata

    """
    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "ping": "/ping",
            "docs": "/docs",
            "documents": "/api/documents",
        },
    }
