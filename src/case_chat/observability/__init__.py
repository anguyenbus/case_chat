"""
Observability module for Case Chat.

This module provides MLflow tracing integration for automatic observability
of agent interactions, including model calls, tool calls, RAG operations,
and document uploads.

Components:
- MLflowSettings: Pydantic-based configuration for MLflow connection
- get_mlflow_settings(): Get cached MLflow configuration instance
- initialize_mlflow_tracing(): Initialize MLflow tracing with Agno autolog

Usage:
    from case_chat.observability import get_mlflow_settings, initialize_mlflow_tracing

    settings = get_mlflow_settings()
    initialize_mlflow_tracing(settings)

Configuration:
    MLflow is configured via environment variables:
    - MLFLOW_TRACKING_URI: MLflow server endpoint (e.g., http://localhost:5000)
    - MLFLOW_EXPERIMENT_NAME: Experiment name (e.g., case-chat-agent)

Example .env configuration:
    MLFLOW_TRACKING_URI=http://localhost:5000
    MLFLOW_EXPERIMENT_NAME=case-chat-agent
"""

from __future__ import annotations

from case_chat.observability.mlflow_config import (
    MLflowSettings,
    _reset_mlflow_settings_cache,
    get_mlflow_settings,
)
from case_chat.observability.mlflow_tracing import initialize_mlflow_tracing

__all__ = [
    "MLflowSettings",
    "get_mlflow_settings",
    "_reset_mlflow_settings_cache",
    "initialize_mlflow_tracing",
]
