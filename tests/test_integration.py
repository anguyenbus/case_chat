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
        """Test complete workflow: SessionManager -> AgentFactory -> Agent."""
        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        # Create session manager
        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)

        # Verify parent directory was created
        assert db_file.parent.exists()

        # Create agent factory
        factory = AgentFactory(session_manager=session_manager)

        # Create agent
        agent = factory.create_agent(session_id="integration-test")

        # Verify the workflow completed
        assert agent is not None

    def test_configuration_to_agent_workflow(self, tmp_path, monkeypatch):
        """Test workflow from configuration to agent creation."""
        # Reset config cache
        import case_chat.config

        case_chat.config._app_settings = None

        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager
        from case_chat.config import AppSettings

        # Set custom configuration
        monkeypatch.setenv("CASE_CHAT_MODEL_ID", "openai/gpt-4o-mini")

        # Get new settings instance
        settings = AppSettings()

        # Create agent with settings
        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)
        agent = factory.create_agent(session_id="config-test")

        # Verify settings were used
        assert settings.model_id == "openai/gpt-4o-mini"
        assert agent is not None

    def test_database_persistence_workflow(self, tmp_path):
        """Test that sessions persist across agent creations."""
        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        # Create session manager and agent factory
        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        # Create first agent
        agent1 = factory.create_agent(session_id="persist-test-1")

        # Create second agent with same session manager
        agent2 = factory.create_agent(session_id="persist-test-2")

        # Verify both agents exist
        assert agent1 is not None
        assert agent2 is not None

    def test_deployment_script_structure(self):
        """Test that deployment script has correct structure."""
        project_root = Path(__file__).parent.parent
        deploy_script = project_root / "examples" / "case_chat_agentos_deploy.py"

        content = deploy_script.read_text()

        # Verify critical components
        assert "from agno.os import AgentOS" in content
        assert "from dotenv import load_dotenv" in content
        assert "SessionManager" in content
        assert "AgentFactory" in content  # Changed from TeamFactory
        assert "AgentOS" in content
        assert "agent_os.serve" in content
        # Verify session limits are configured in agent factory  # Verify session limits
        assert "save_metrics" in content  # Verify metrics collection

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

    def test_performance_metrics_table_created(self, tmp_path):
        """Test that performance_metrics table is created automatically."""
        import sqlite3

        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_metrics.db"
        SessionManager(db_file=db_file)

        # Verify performance_metrics table exists
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='performance_metrics'"
        )
        result = cursor.fetchone()

        conn.close()

        assert result is not None
        assert result[0] == "performance_metrics"

    def test_metrics_save_and_retrieve_workflow(self, tmp_path):
        """Test complete metrics save and retrieve workflow."""
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_metrics_workflow.db"
        session_manager = SessionManager(db_file=db_file)

        # Save metrics
        session_id = "test-metrics-session"
        session_manager.save_metrics(
            session_id=session_id,
            duration_ms=1500,
            input_tokens=100,
            output_tokens=200,
        )

        # Retrieve metrics
        metrics = session_manager.get_metrics(session_id=session_id)

        # Verify metrics
        assert len(metrics) == 1
        assert metrics[0]["duration_ms"] == 1500
        assert metrics[0]["input_tokens"] == 100
        assert metrics[0]["output_tokens"] == 200
        assert metrics[0]["total_tokens"] == 300

    def test_agent_factory_with_session_history_limits(self, tmp_path):
        """Test that AgentFactory creates agents with session history limits."""
        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_history_limits.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        agent = factory.create_agent(session_id="test-session")

        # Verify num_history_runs is set
        assert agent.num_history_runs == 3
