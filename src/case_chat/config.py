"""
Configuration management for Case Chat.

Handles loading configuration from environment variables and .env files.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Models
# ============================================================================


def _get_env_file() -> str | None:
    """
    Get the .env file path, respecting CASE_CHAT_SKIP_ENV_FILE.

    Returns None if CASE_CHAT_SKIP_ENV_FILE is set (for testing).

    Returns
    -------
    str | None
        Path to .env file or None

    """
    if os.environ.get("CASE_CHAT_SKIP_ENV_FILE"):
        return None
    return ".env"


def _make_model_config(env_prefix: str) -> SettingsConfigDict:
    """
    Create SettingsConfigDict with conditional .env file loading.

    Parameters
    ----------
    env_prefix : str
        Environment variable prefix

    Returns
    -------
    SettingsConfigDict
        Configuration dict for Pydantic settings

    """
    return SettingsConfigDict(
        env_prefix=env_prefix,
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


class AppSettings(BaseSettings):
    """
    Application settings.

    Loads from environment variables with prefix CASE_CHAT_.
    NOTE: Field names with underscores map to CASE_CHAT_FIELDNAME env vars.
    """

    model_config = _make_model_config("CASE_CHAT_")

    environment: str = Field(default="development", description="Deployment environment")
    log_level: str = Field(default="INFO", description="Logging level")
    model_id: str = Field(
        default="glm-5",
        description="Default model ID for agent",
    )

    # Document and RAG configuration
    chroma_db_path: Path = Field(
        default="data/chroma",
        description="Path to ChromaDB vector storage",
    )
    documents_path: Path = Field(
        default="data/documents",
        description="Path to uploaded document storage",
    )
    max_file_size_mb: int = Field(
        default=50,
        description="Maximum file size in MB for uploads",
    )
    chunk_size_tokens: int = Field(
        default=750,
        description="Target chunk size in tokens",
    )
    chunk_overlap_pct: int = Field(
        default=10,
        description="Chunk overlap percentage (0-100)",
    )
    allowed_file_types: list[str] = Field(
        default=[".pdf", ".txt", ".docx"],
        description="Allowed file extensions for upload",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid Python logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper

    @field_validator("chunk_overlap_pct")
    @classmethod
    def validate_chunk_overlap_pct(cls, v: int) -> int:
        """Validate chunk overlap percentage is between 0 and 100."""
        if not 0 <= v <= 100:
            raise ValueError(f"Chunk overlap must be between 0 and 100, got {v}")
        return v

    @field_validator("max_file_size_mb")
    @classmethod
    def validate_max_file_size_mb(cls, v: int) -> int:
        """Validate maximum file size is positive."""
        if v <= 0:
            raise ValueError(f"Max file size must be positive, got {v}")
        return v

    @field_validator("allowed_file_types")
    @classmethod
    def validate_allowed_file_types(cls, v: list[str]) -> list[str]:
        """Validate allowed file types start with dot."""
        for file_type in v:
            if not file_type.startswith("."):
                raise ValueError(f"File type must start with '.', got {file_type}")
        return v


# ============================================================================
# Global Configuration Instance
# ============================================================================

# Global configuration cache
_app_settings: AppSettings | None = None


def _load_env_file() -> bool:
    """
    Load the .env file from project root.

    Returns True if file was found and loaded, False otherwise.

    This follows golden path pattern with try/except/else.
    """
    try:
        # Skip .env loading if CASE_CHAT_SKIP_ENV_FILE is set (for testing)
        if os.environ.get("CASE_CHAT_SKIP_ENV_FILE"):
            return False

        # Find .env file in project root
        project_root = Path(__file__).parent.parent.parent
        env_file = project_root / ".env"

        if not env_file.exists():
            logger.debug("No .env file found at %s", env_file)
            return False

        # Load .env file using python-dotenv
        from dotenv import load_dotenv

        loaded = load_dotenv(env_file)

        if loaded:
            logger.info("Loaded .env file from %s", env_file)

        return loaded

    except Exception as e:
        logger.error("Failed to load .env file: %s", e)
        # Re-raise to signal failure
        raise
    else:
        # Success - env file loaded (or didn't exist, which is ok)
        return True


def get_app_settings() -> AppSettings:
    """
    Get application settings, loading from environment.

    Returns cached settings after first call.

    Returns
    -------
    AppSettings
        Application settings

    Examples
    --------
    >>> settings = get_app_settings()
    >>> print(settings.environment)
    'development'

    """
    global _app_settings

    try:
        if _app_settings is None:
            # Load .env file if not already loaded
            _load_env_file()

            # Create settings instance
            _app_settings = AppSettings()

        return _app_settings

    except Exception as e:
        logger.error("Failed to initialize app settings: %s", e)
        raise
    else:
        return _app_settings


# NOTE: Function to reset configuration cache (useful for testing)
def _reset_config_cache() -> None:
    """Reset cached configuration instances. Primarily for testing."""
    global _app_settings
    _app_settings = None
