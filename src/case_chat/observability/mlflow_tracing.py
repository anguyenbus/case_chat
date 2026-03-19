"""
MLflow tracing initialization for Case Chat observability.

Handles MLflow server configuration, Agno autolog enablement, and
connectivity validation for OpenTelemetry-native trace capture.
"""

from __future__ import annotations

import logging
from typing import Final

import requests

from case_chat.observability.mlflow_config import MLflowSettings

# Configure logging
logger = logging.getLogger(__name__)

# Constants for MLflow connectivity validation
MLFLOW_HEALTH_TIMEOUT: Final[int] = 5  # seconds


def _validate_mlflow_server_connectivity(settings: MLflowSettings) -> None:
    """
    Validate MLflow server is reachable and healthy.

    Performs a health check on the MLflow server to ensure it's accessible
    before attempting to initialize tracing. This prevents hanging on
    unreachable servers and provides clear error messages.

    Parameters
    ----------
    settings : MLflowSettings
        MLflow configuration settings

    Raises
    ------
    ConnectionError
        If MLflow server is unreachable or returns an error status

    Examples
    --------
    >>> settings = MLflowSettings(
    ...     tracking_uri="http://localhost:5000", experiment_name="case-chat-agent"
    ... )
    >>> _validate_mlflow_server_connectivity(settings)
    # Raises ConnectionError if server is unreachable

    """
    health_url = f"{settings.tracking_uri}/health"

    try:
        logger.debug("[MLFLOW] Checking MLflow server connectivity at %s", health_url)

        response = requests.get(
            health_url,
            timeout=MLFLOW_HEALTH_TIMEOUT,
        )

        # Accept 2xx status codes
        if not 200 <= response.status_code < 300:
            raise ConnectionError(
                f"MLflow server returned status {response.status_code}. "
                f"Expected 200 OK. Check server is running at: {settings.tracking_uri}"
            )

        logger.info("[MLFLOW] Server connectivity validated: %s", settings.tracking_uri)

    except requests.exceptions.Timeout as e:
        raise ConnectionError(
            f"MLflow server connection timed out after {MLFLOW_HEALTH_TIMEOUT}s. "
            f"Check server is running at: {settings.tracking_uri}"
        ) from e
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(
            f"Cannot connect to MLflow server at {settings.tracking_uri}. "
            f"Ensure MLflow server is running. Error: {e!s}"
        ) from e
    except Exception as e:
        raise ConnectionError(
            f"Failed to validate MLflow server connectivity: {e!s}. "
            f"Check server is running at: {settings.tracking_uri}"
        ) from e


def initialize_mlflow_tracing(settings: MLflowSettings) -> None:
    """
    Initialize MLflow tracing with Agno autolog for OpenTelemetry trace capture.

    Configures MLflow tracking URI and experiment name, then enables Agno
    autolog for automatic instrumentation of agent interactions. This captures
    all model calls, tool calls, RAG operations, and document uploads.

    Parameters
    ----------
    settings : MLflowSettings
        MLflow configuration settings. Must include valid tracking_uri and
        experiment_name. Required - no defaults for explicit configuration.

    Raises
    ------
    ConnectionError
        If MLflow server is unreachable or validation fails
    ValueError
        If MLflow configuration is invalid

    Examples
    --------
    >>> from case_chat.observability import (
    ...     get_mlflow_settings,
    ...     initialize_mlflow_tracing,
    ... )
    >>> settings = get_mlflow_settings()
    >>> initialize_mlflow_tracing(settings)
    [MLFLOW] Initializing MLflow tracing...
    [MLFLOW] Tracking URI: http://localhost:5000
    [MLFLOW] Experiment: case-chat-agent
    [MLFLOW] View traces: http://localhost:5000/#/experiments/1

    Notes
    -----
    This function enables full tracing scope including:
    - LLM model calls (requests, responses, latency, token usage)
    - Tool/function calls (inputs, outputs, execution time, errors)
    - RAG operations (vector searches, retrieval, ranking)
    - Document uploads (parsing, chunking, embedding, storage)
    - Agent steps (reasoning traces, decisions, context)

    Uses mlflow.agno.autolog() for automatic instrumentation following
    Agno framework conventions for OpenTelemetry-compatible traces.

    """
    logger.info("[MLFLOW] Initializing MLflow tracing...")

    try:
        # Import mlflow here to allow testing without mlflow installed
        import mlflow

        # Validate MLflow server connectivity before proceeding
        _validate_mlflow_server_connectivity(settings)

        # Configure MLflow tracking URI
        mlflow.set_tracking_uri(settings.tracking_uri)
        logger.info("[MLFLOW] Tracking URI configured: %s", settings.tracking_uri)

        # Configure MLflow experiment
        mlflow.set_experiment(settings.experiment_name)
        logger.info("[MLFLOW] Experiment configured: %s", settings.experiment_name)

        # Enable Agno autolog for automatic instrumentation
        # NOTE: This captures all agent interactions automatically
        mlflow.agno.autolog()

        # Log successful initialization
        logger.info("[MLFLOW] Tracing initialized successfully")
        logger.info("[MLFLOW] View traces: %s/#/experiments/", settings.tracking_uri)
        logger.info("[MLFLOW] Tracing scope: model calls, tools, RAG operations, document uploads")

    except ConnectionError:
        # Re-raise connection errors with additional context
        logger.error(
            "[MLFLOW] Failed to initialize MLflow tracing: server unreachable at %s",
            settings.tracking_uri,
        )
        raise
    except Exception as e:
        logger.error("[MLFLOW] Failed to initialize MLflow tracing: %s", e)
        raise ValueError(f"MLflow tracing initialization failed: {e!s}") from e
    else:
        # Success path - log completion
        logger.info("[MLFLOW] Initialization complete - traces will be captured automatically")
