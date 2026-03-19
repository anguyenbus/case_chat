"""
Tests for MLflow tracing initialization module.

Tests initialize_mlflow_tracing() function and server connectivity validation.
Follows TDD approach with focused, isolated test cases.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from case_chat.observability.mlflow_config import MLflowSettings
from case_chat.observability.mlflow_tracing import initialize_mlflow_tracing


class TestInitializeMlflowTracing:
    """Test initialize_mlflow_tracing() function."""

    def test_successful_initialization_with_valid_settings(self, caplog):
        """Test successful initialization with valid MLflowSettings object."""
        settings = MLflowSettings(
            tracking_uri="http://localhost:5000",
            experiment_name="case-chat-agent",
        )

        with caplog.at_level(logging.INFO):
            # Mock mlflow import inside the function
            with patch("builtins.__import__") as mock_import:
                # Create mock mlflow module
                mock_mlflow = MagicMock()
                mock_import.side_effect = lambda name, *args, **kwargs: (
                    mock_mlflow if name == "mlflow" else __import__(name, *args, **kwargs)
                )

                with patch(
                    "case_chat.observability.mlflow_tracing._validate_mlflow_server_connectivity"
                ):
                    initialize_mlflow_tracing(settings)

        # Verify MLflow configuration
        assert mock_mlflow.set_tracking_uri.called
        assert mock_mlflow.set_experiment.called
        assert mock_mlflow.agno.autolog.called

        # Verify logging
        assert "[MLFLOW]" in caplog.text
        assert "Initializing MLflow tracing" in caplog.text
        assert "Tracking URI configured: http://localhost:5000" in caplog.text
        assert "Experiment configured: case-chat-agent" in caplog.text

    def test_error_handling_when_mlflow_server_unreachable(self, caplog):
        """Test error handling when MLflow server is unreachable."""
        settings = MLflowSettings(
            tracking_uri="http://localhost:5000",
            experiment_name="case-chat-agent",
        )

        with caplog.at_level(logging.ERROR):
            with patch(
                "case_chat.observability.mlflow_tracing._validate_mlflow_server_connectivity",
                side_effect=ConnectionError("Server unreachable"),
            ):
                with pytest.raises(ConnectionError, match="Server unreachable"):
                    initialize_mlflow_tracing(settings)

        # Verify error logging
        assert "[MLFLOW]" in caplog.text
        assert "Failed to initialize MLflow tracing" in caplog.text

    def test_verifies_mlflow_tracking_uri_configured_correctly(self):
        """Verify MLflow tracking URI is configured correctly."""
        settings = MLflowSettings(
            tracking_uri="http://localhost:5000",
            experiment_name="case-chat-agent",
        )

        with patch("builtins.__import__") as mock_import:
            mock_mlflow = MagicMock()
            mock_import.side_effect = lambda name, *args, **kwargs: (
                mock_mlflow if name == "mlflow" else __import__(name, *args, **kwargs)
            )

            with patch(
                "case_chat.observability.mlflow_tracing._validate_mlflow_server_connectivity"
            ):
                initialize_mlflow_tracing(settings)

        # Verify set_tracking_uri was called with correct value
        mock_mlflow.set_tracking_uri.assert_called_once_with("http://localhost:5000")

    def test_verifies_mlflow_experiment_name_configured_correctly(self):
        """Verify MLflow experiment name is configured correctly."""
        settings = MLflowSettings(
            tracking_uri="http://localhost:5000",
            experiment_name="test-experiment",
        )

        with patch("builtins.__import__") as mock_import:
            mock_mlflow = MagicMock()
            mock_import.side_effect = lambda name, *args, **kwargs: (
                mock_mlflow if name == "mlflow" else __import__(name, *args, **kwargs)
            )

            with patch(
                "case_chat.observability.mlflow_tracing._validate_mlflow_server_connectivity"
            ):
                initialize_mlflow_tracing(settings)

        # Verify set_experiment was called with correct value
        mock_mlflow.set_experiment.assert_called_once_with("test-experiment")

    def test_verifies_mlflow_agno_autolog_is_called_and_enabled(self):
        """Verify mlflow.agno.autolog() is called and enabled."""
        settings = MLflowSettings(
            tracking_uri="http://localhost:5000",
            experiment_name="case-chat-agent",
        )

        with patch("builtins.__import__") as mock_import:
            mock_mlflow = MagicMock()
            mock_import.side_effect = lambda name, *args, **kwargs: (
                mock_mlflow if name == "mlflow" else __import__(name, *args, **kwargs)
            )

            with patch(
                "case_chat.observability.mlflow_tracing._validate_mlflow_server_connectivity"
            ):
                initialize_mlflow_tracing(settings)

        # Verify autolog was called
        mock_mlflow.agno.autolog.assert_called_once()

    def test_logging_output_format_and_content(self, caplog):
        """Test logging output format and content (verify [MLFLOW] tag prefix)."""
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

        # Verify [MLFLOW] tag prefix (NO EMOJIS)
        mlflow_logs = [record for record in caplog.records if "[MLFLOW]" in record.message]
        assert len(mlflow_logs) > 0, "Expected [MLFLOW] tagged logs"

        # Verify no emoji characters in logs
        for record in caplog.records:
            message = record.message
            # Check for common emojis (should not be present)
            assert not any(
                emoji in message for emoji in ["🚀", "✅", "❌", "⚠️", "📊", "🔍", "💡", "🎯"]
            ), f"Emoji found in log message: {message}"

        # Verify expected log content
        log_text = caplog.text
        assert "Tracking URI configured: http://localhost:5000" in log_text
        assert "Experiment configured: case-chat-agent" in log_text
        assert "model calls" in log_text.lower()
        assert "tools" in log_text.lower()
