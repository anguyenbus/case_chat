"""
Tests for application configuration.

Tests configuration loading from environment variables.
"""

from __future__ import annotations


class TestAppSettings:
    """Test application settings configuration."""

    def test_app_settings_loads_from_environment(self, monkeypatch):
        """Test that AppSettings loads from environment variables."""
        from case_chat.config import AppSettings

        # Set environment variables
        monkeypatch.setenv("CASE_CHAT_ENVIRONMENT", "test")
        monkeypatch.setenv("CASE_CHAT_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("CASE_CHAT_MODEL_ID", "openai/gpt-4o-mini")

        # Create settings instance
        settings = AppSettings()

        assert settings.environment == "test"
        assert settings.log_level == "DEBUG"
        assert settings.model_id == "openai/gpt-4o-mini"

    def test_app_settings_has_defaults(self, monkeypatch):
        """Test that AppSettings has correct default values."""
        from case_chat.config import AppSettings

        # Clear environment variables
        monkeypatch.delenv("CASE_CHAT_ENVIRONMENT", raising=False)
        monkeypatch.delenv("CASE_CHAT_LOG_LEVEL", raising=False)
        monkeypatch.delenv("CASE_CHAT_MODEL_ID", raising=False)

        # Create settings instance
        settings = AppSettings()

        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.model_id == "glm-5"

    def test_get_app_settings_caching(self, monkeypatch):
        """Test that get_app_settings() returns cached instance."""
        # Clear config cache
        import case_chat.config
        from case_chat.config import get_app_settings

        case_chat.config._app_settings = None

        # Get settings twice
        settings1 = get_app_settings()
        settings2 = get_app_settings()

        assert settings1 is settings2

    def test_skip_env_file_works(self, monkeypatch, tmp_path):
        """Test that CASE_CHAT_SKIP_ENV_FILE skips .env loading."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text("CASE_CHAT_ENVIRONMENT=fromenv")

        # Set skip flag
        monkeypatch.setenv("CASE_CHAT_SKIP_ENV_FILE", "1")

        # The skip flag should be respected
        # (We can't fully test this without actually loading .env,
        # but we can verify the flag is checked)
        from case_chat.config import _get_env_file

        result = _get_env_file()
        assert result is None
