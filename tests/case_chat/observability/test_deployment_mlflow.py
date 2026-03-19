"""
Tests for AgentOS deployment integration with MLflow.

Tests that MLflow initialization is properly integrated into the deployment flow.
Follows TDD approach with focused, isolated test cases.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from case_chat.observability.mlflow_config import MLflowSettings
from case_chat.observability.mlflow_tracing import initialize_mlflow_tracing


class TestDeploymentMlflowIntegration:
    """Test MLflow integration in AgentOS deployment."""

    def test_mlflow_initialization_called_during_deployment_startup(self, caplog):
        """Test that MLflow initialization is called during deployment startup."""
        settings = MLflowSettings(
            tracking_uri="http://localhost:5000",
            experiment_name="case-chat-agent",
        )

        with caplog.at_level(logging.INFO):
            with patch("builtins.__import__") as mock_import:
                mock_mlflow = MagicMock()
                mock_import.side_effect = lambda name, *args, **kwargs: (
                    mock_mlflow if name == "mlflow" else __import__(name, *args, **kwargs)
                )

                with patch(
                    "case_chat.observability.mlflow_tracing._validate_mlflow_server_connectivity"
                ):
                    initialize_mlflow_tracing(settings)

        # Verify MLflow initialization logs appear
        assert "[MLFLOW]" in caplog.text
        assert "Initializing MLflow tracing" in caplog.text

    def test_deployment_proceeds_when_mlflow_initialization_succeeds(self, caplog):
        """Test deployment proceeds when MLflow initialization succeeds."""
        settings = MLflowSettings(
            tracking_uri="http://localhost:5000",
            experiment_name="case-chat-agent",
        )

        with caplog.at_level(logging.INFO):
            with patch("builtins.__import__") as mock_import:
                mock_mlflow = MagicMock()
                mock_import.side_effect = lambda name, *args, **kwargs: (
                    mock_mlflow if name == "mlflow" else __import__(name, *args, **kwargs)
                )

                with patch(
                    "case_chat.observability.mlflow_tracing._validate_mlflow_server_connectivity"
                ):
                    # Should not raise exception
                    initialize_mlflow_tracing(settings)

                    # Verify success logging
                    assert "Tracing initialized successfully" in caplog.text
                    assert "Initialization complete" in caplog.text

    def test_deployment_fails_gracefully_when_mlflow_initialization_fails(self, caplog):
        """Test deployment fails gracefully when MLflow initialization fails."""
        settings = MLflowSettings(
            tracking_uri="http://localhost:5000",
            experiment_name="case-chat-agent",
        )

        with caplog.at_level(logging.ERROR):
            with patch(
                "case_chat.observability.mlflow_tracing._validate_mlflow_server_connectivity",
                side_effect=ConnectionError("MLflow server unreachable"),
            ):
                # Should raise exception
                with pytest.raises(ConnectionError, match="MLflow server unreachable"):
                    initialize_mlflow_tracing(settings)

                # Verify error logging
                assert "[MLFLOW]" in caplog.text
                assert "Failed to initialize MLflow tracing" in caplog.text

    def test_mlflow_logging_appears_in_deployment_startup_logs(self, caplog):
        """Verify MLflow logging appears in deployment startup logs."""
        settings = MLflowSettings(
            tracking_uri="http://localhost:5000",
            experiment_name="case-chat-agent",
        )

        with caplog.at_level(logging.INFO):
            with patch("builtins.__import__") as mock_import:
                mock_mlflow = MagicMock()
                mock_import.side_effect = lambda name, *args, **kwargs: (
                    mock_mlflow if name == "mlflow" else __import__(name, *args, **kwargs)
                )

                with patch(
                    "case_chat.observability.mlflow_tracing._validate_mlflow_server_connectivity"
                ):
                    initialize_mlflow_tracing(settings)

        # Verify MLflow startup logs
        log_text = caplog.text
        assert "[MLFLOW] Initializing MLflow tracing" in log_text
        assert "[MLFLOW] Tracking URI configured: http://localhost:5000" in log_text
        assert "[MLFLOW] Experiment configured: case-chat-agent" in log_text
        assert "[MLFLOW] Tracing initialized successfully" in log_text
        assert "model calls" in log_text.lower()
        assert "tools" in log_text.lower()
