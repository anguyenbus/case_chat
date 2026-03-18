"""
Tests for AgentFactory.

Tests agent creation and factory functionality.
"""

from __future__ import annotations


class TestAgentFactory:
    """Test AgentFactory for agent creation."""

    def test_agent_factory_initialization(self, tmp_path):
        """Test AgentFactory initialization with SessionManager."""
        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)

        factory = AgentFactory(session_manager=session_manager)

        assert factory.session_manager is session_manager

    def test_create_agent_returns_agent_not_team(self, tmp_path):
        """Test that create_agent() returns an Agent, not a Team."""
        from agno.agent import Agent

        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        result = factory.create_agent(session_id="test-session")

        # Result should be an Agent, not a Team
        assert isinstance(result, Agent)
        assert not hasattr(result, "members")

    def test_agent_has_correct_name(self, tmp_path):
        """Test that agent has correct name: 'case-chat-assistant'."""
        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        agent = factory.create_agent(session_id="test-session")

        assert agent.name == "case-chat-assistant"

    def test_agent_has_database_attached(self, tmp_path):
        """Test that agent has database attached (SqliteDb instance)."""
        from agno.db.sqlite import SqliteDb

        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        agent = factory.create_agent(session_id="test-session")

        # Check if agent has db attached
        assert agent.db is not None
        assert isinstance(agent.db, SqliteDb)

    def test_markdown_output_enabled(self, tmp_path):
        """Test that markdown output is enabled."""
        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        agent = factory.create_agent(session_id="test-session")

        # Check markdown is enabled
        assert agent.markdown is True

    def test_agent_configured_with_num_history_runs(self, tmp_path):
        """Test that agent is configured with num_history_runs=3."""
        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        agent = factory.create_agent(session_id="test-session")

        # Check num_history_runs is set to 3
        assert agent.num_history_runs == 3

    def test_agent_session_id_set_correctly(self, tmp_path):
        """Test that agent session_id is set correctly."""
        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        session_id = "my-custom-session"
        agent = factory.create_agent(session_id=session_id)

        assert agent.session_id == session_id

    def test_agent_instructions_contain_tax_law_guidance(self, tmp_path):
        """Test that agent instructions contain tax law guidance."""
        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        agent = factory.create_agent(session_id="test-session")

        # Check instructions exist and contain relevant content
        assert agent.instructions is not None
        assert len(agent.instructions) > 0
        instruction_text = " ".join(agent.instructions)
        assert "tax law" in instruction_text.lower()
        assert "markdown" in instruction_text.lower()
