"""
MLflow configuration management for Case Chat observability.

Handles loading MLflow configuration from environment variables and .env files.
Follows the same pattern as config.py for consistency.
"""

from __future__ import annotations

import logging

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Import configuration helpers from existing config module
from case_chat.config import _get_env_file, _load_env_file

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Models
# ============================================================================


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


class MLflowSettings(BaseSettings):
    """
    MLflow tracing configuration.

    Loads from environment variables with prefix MLFLOW_.
    NOTE: Field names with underscores map to MLFLOW_FIELDNAME env vars.

    Attributes
    ----------
    tracking_uri : str
        MLflow server endpoint (required). Must start with http:// or https://.
    experiment_name : str
        MLflow experiment name (required). Groups related runs together.

    Examples
    --------
    >>> # Set environment variables
    >>> os.environ["MLFLOW_TRACKING_URI"] = "http://localhost:5000"
    >>> os.environ["MLFLOW_EXPERIMENT_NAME"] = "case-chat-agent"
    >>> settings = MLflowSettings()
    >>> print(settings.tracking_uri)
    'http://localhost:5000'

    """

    model_config = _make_model_config("MLFLOW_")

    tracking_uri: str = Field(
        ...,
        description="MLflow server endpoint (e.g., http://localhost:5000)",
    )
    experiment_name: str = Field(
        ...,
        description="MLflow experiment name for grouping runs",
    )

    @field_validator("tracking_uri")
    @classmethod
    def validate_tracking_uri(cls, v: str) -> str:
        """
        Validate MLflow tracking URI format and security.

        Ensures URI starts with http:// or https:// to prevent SSRF attacks.

        Parameters
        ----------
        v : str
            Tracking URI to validate

        Returns
        -------
        str
            Validated tracking URI

        Raises
        ------
        ValueError
            If URI doesn't start with http:// or https://

        """
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"MLflow tracking URI must start with http:// or https://, got: {v}")

        # NOTE: For local POC development, we allow localhost URIs.
        # In production, additional validation should be added to restrict
        # to approved MLflow server endpoints.

        return v


# ============================================================================
# Global Configuration Instance
# ============================================================================

# Global configuration cache
_mlflow_settings: MLflowSettings | None = None


def get_mlflow_settings() -> MLflowSettings:
    """
    Get MLflow settings, loading from environment.

    Returns cached settings after first call.

    Returns
    -------
    MLflowSettings
        MLflow configuration settings

    Raises
    ------
    ValueError
        If required environment variables are not set

    Examples
    --------
    >>> settings = get_mlflow_settings()
    >>> print(settings.tracking_uri)
    'http://localhost:5000'

    """
    global _mlflow_settings

    try:
        if _mlflow_settings is None:
            # Load .env file if not already loaded
            _load_env_file()

            # Create settings instance
            _mlflow_settings = MLflowSettings()

        return _mlflow_settings

    except Exception as e:
        logger.error("[MLFLOW] Failed to initialize MLflow settings: %s", e)
        raise
    else:
        return _mlflow_settings


# NOTE: Function to reset configuration cache (useful for testing)
def _reset_mlflow_settings_cache() -> None:
    """
    Reset cached MLflow configuration instances.

    Primarily for testing to ensure test isolation.

    """
    global _mlflow_settings
    _mlflow_settings = None
