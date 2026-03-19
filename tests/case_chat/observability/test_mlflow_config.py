"""
Tests for MLflow configuration module.

Tests MLflowSettings class, get_mlflow_settings() function, and cache reset.
Follows TDD approach with focused, isolated test cases.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from case_chat.observability.mlflow_config import (
    MLflowSettings,
    _reset_mlflow_settings_cache,
    get_mlflow_settings,
)


class TestMLflowSettings:
    """Test MLflowSettings configuration class."""

    def test_successful_settings_creation_with_valid_env_vars(self, monkeypatch):
        """Test successful settings creation with valid environment variables."""
        monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        monkeypatch.setenv("MLFLOW_EXPERIMENT_NAME", "case-chat-agent")

        settings = MLflowSettings()

        assert settings.tracking_uri == "http://localhost:5000"
        assert settings.experiment_name == "case-chat-agent"

    def test_validation_failure_when_tracking_uri_missing(self, monkeypatch):
        """Test validation failure when MLFLOW_TRACKING_URI is missing."""
        monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
        monkeypatch.setenv("MLFLOW_EXPERIMENT_NAME", "case-chat-agent")

        with pytest.raises(ValidationError):
            MLflowSettings()

    def test_validation_failure_when_experiment_name_missing(self, monkeypatch):
        """Test validation failure when MLFLOW_EXPERIMENT_NAME is missing."""
        monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        monkeypatch.delenv("MLFLOW_EXPERIMENT_NAME", raising=False)

        with pytest.raises(ValidationError):
            MLflowSettings()

    def test_validation_failure_for_invalid_uri_format_no_prefix(self, monkeypatch):
        """Test validation failure for invalid URI format (no http:// or https:// prefix)."""
        monkeypatch.setenv("MLFLOW_TRACKING_URI", "localhost:5000")
        monkeypatch.setenv("MLFLOW_EXPERIMENT_NAME", "case-chat-agent")

        with pytest.raises(ValueError, match="MLflow tracking URI must start with"):
            MLflowSettings()

    def test_settings_caching_behavior_singleton_pattern(self, monkeypatch):
        """Test settings caching behavior (singleton pattern)."""
        monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        monkeypatch.setenv("MLFLOW_EXPERIMENT_NAME", "case-chat-agent")

        # Reset cache first
        _reset_mlflow_settings_cache()

        settings1 = get_mlflow_settings()
        settings2 = get_mlflow_settings()

        # Should return the same cached instance
        assert settings1 is settings2
        assert id(settings1) == id(settings2)

    def test_reset_mlflow_settings_cache_function(self, monkeypatch):
        """Test _reset_mlflow_settings_cache() function for test isolation."""
        monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        monkeypatch.setenv("MLFLOW_EXPERIMENT_NAME", "case-chat-agent")

        # Get first instance
        settings1 = get_mlflow_settings()
        settings_id_1 = id(settings1)

        # Reset cache
        _reset_mlflow_settings_cache()

        # Get new instance after reset
        settings2 = get_mlflow_settings()
        settings_id_2 = id(settings2)

        # Should be different instances
        assert settings1 is not settings2
        assert settings_id_1 != settings_id_2
