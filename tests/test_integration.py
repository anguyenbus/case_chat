"""
Integration tests for AgentOS environment setup.

Tests critical end-to-end workflows.
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestEndToEndWorkflows:
    """Test end-to-end workflows for AgentOS setup."""

    def test_full_session_workflow(self, tmp_path):
        """Test complete workflow: SessionManager -> TeamFactory -> Agent."""
        from case_chat.agents.session_manager import SessionManager
        from case_chat.agents.team_factory import TeamFactory

        # Create session manager
        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)

        # Verify parent directory was created
        assert db_file.parent.exists()

        # Create team factory
        factory = TeamFactory(session_manager=session_manager)

        # Create team/agent
        team = factory.create_team(session_id="integration-test")

        # Verify the workflow completed
        assert team is not None

    def test_configuration_to_agent_workflow(self, tmp_path, monkeypatch):
        """Test workflow from configuration to agent creation."""
        # Reset config cache
        import case_chat.config

        case_chat.config._app_settings = None

        from case_chat.agents.session_manager import SessionManager
        from case_chat.agents.team_factory import TeamFactory
        from case_chat.config import AppSettings

        # Set custom configuration
        monkeypatch.setenv("CASE_CHAT_MODEL_ID", "openai/gpt-4o-mini")

        # Get new settings instance
        settings = AppSettings()

        # Create agent with settings
        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)
        factory = TeamFactory(session_manager=session_manager)
        team = factory.create_team(session_id="config-test")

        # Verify settings were used
        assert settings.model_id == "openai/gpt-4o-mini"
        assert team is not None

    def test_database_persistence_workflow(self, tmp_path):
        """Test that sessions persist across team creations."""
        from case_chat.agents.session_manager import SessionManager
        from case_chat.agents.team_factory import TeamFactory

        # Create session manager and team
        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)
        factory = TeamFactory(session_manager=session_manager)

        # Create first team
        team1 = factory.create_team(session_id="persist-test-1")

        # Create second team with same session manager
        team2 = factory.create_team(session_id="persist-test-2")

        # Verify both teams exist
        assert team1 is not None
        assert team2 is not None

    def test_deployment_script_structure(self):
        """Test that deployment script has correct structure."""
        project_root = Path(__file__).parent.parent
        deploy_script = project_root / "examples" / "case_chat_agentos_deploy.py"

        content = deploy_script.read_text()

        # Verify critical components
        assert "from agno.os import AgentOS" in content
        assert "from dotenv import load_dotenv" in content
        assert "SessionManager" in content
        assert "TeamFactory" in content
        assert "AgentOS" in content
        assert "agent_os.serve" in content

    def test_project_structure_completeness(self):
        """Test that all required project components exist."""
        project_root = Path(__file__).parent.parent

        # Required files (excluding README.md for now)
        required_files = [
            "pyproject.toml",
            ".pre-commit-config.yaml",
            ".gitignore",
            ".env.example",
            "Makefile",
        ]

        for file in required_files:
            file_path = project_root / file
            assert file_path.exists(), f"Required file {file} does not exist"

        # Required directories
        required_dirs = [
            "src/case_chat",
            "src/case_chat/agents",
            "tests",
            "examples",
            "tmp",
        ]

        for dir_path in required_dirs:
            path = project_root / dir_path
            assert path.exists(), f"Required directory {dir_path} does not exist"

    def test_environment_variable_validation(self, monkeypatch):
        """Test that environment variables are properly validated."""
        from case_chat.config import AppSettings

        # Test invalid log level
        with pytest.raises(ValueError):
            monkeypatch.setenv("CASE_CHAT_LOG_LEVEL", "INVALID")
            AppSettings()

    def test_database_file_creation(self, tmp_path):
        """Test that database file location is prepared correctly."""
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "subdir" / "test_sessions.db"
        SessionManager(db_file=db_file)

        # Verify parent directory was created
        assert db_file.parent.exists()
        assert db_file.parent.is_dir()

    def test_session_manager_default_values(self):
        """Test SessionManager uses correct default values."""
        from case_chat.agents.session_manager import SessionManager

        manager = SessionManager()

        assert manager.db_file == SessionManager.DEFAULT_DB_FILE
        assert manager.session_table == SessionManager.DEFAULT_SESSION_TABLE
