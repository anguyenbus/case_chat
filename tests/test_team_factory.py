"""
Tests for TeamFactory.

Tests agent creation and team factory functionality.
"""

from __future__ import annotations


class TestTeamFactory:
    """Test TeamFactory for agent creation."""

    def test_team_factory_initialization(self, tmp_path):
        """Test TeamFactory initialization with SessionManager."""
        from case_chat.agents.session_manager import SessionManager
        from case_chat.agents.team_factory import TeamFactory

        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)

        factory = TeamFactory(session_manager=session_manager)

        assert factory.session_manager is session_manager

    def test_create_team_returns_valid_result(self, tmp_path):
        """Test that create_team() returns a valid result."""
        from case_chat.agents.session_manager import SessionManager
        from case_chat.agents.team_factory import TeamFactory

        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)
        factory = TeamFactory(session_manager=session_manager)

        result = factory.create_team(session_id="test-session")

        assert result is not None

    def test_agent_has_correct_name(self, tmp_path):
        """Test that agent has correct name."""
        from case_chat.agents.session_manager import SessionManager
        from case_chat.agents.team_factory import TeamFactory

        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)
        factory = TeamFactory(session_manager=session_manager)

        result = factory.create_team(session_id="test-session")

        # Result can be either a Team or an Agent
        # If it's a Team, get the first member
        if hasattr(result, "members"):
            agent = result.members[0]
        else:
            agent = result

        assert agent.name == "case-chat-assistant"

    def test_agent_has_database_attached(self, tmp_path):
        """Test that agent has database attached."""
        from agno.db.sqlite import SqliteDb

        from case_chat.agents.session_manager import SessionManager
        from case_chat.agents.team_factory import TeamFactory

        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)
        factory = TeamFactory(session_manager=session_manager)

        result = factory.create_team(session_id="test-session")

        # Result can be either a Team or an Agent
        if hasattr(result, "members"):
            agent = result.members[0]
        else:
            agent = result

        # Check if agent has db attached
        assert agent.db is not None
        assert isinstance(agent.db, SqliteDb)

    def test_markdown_output_enabled(self, tmp_path):
        """Test that markdown output is enabled."""
        from case_chat.agents.session_manager import SessionManager
        from case_chat.agents.team_factory import TeamFactory

        db_file = tmp_path / "test_sessions.db"
        session_manager = SessionManager(db_file=db_file)
        factory = TeamFactory(session_manager=session_manager)

        result = factory.create_team(session_id="test-session")

        # Result can be either a Team or an Agent
        if hasattr(result, "members"):
            agent = result.members[0]
        else:
            agent = result

        # Check markdown instructions
        assert agent.instructions is not None
        assert len(agent.instructions) > 0
        assert agent.markdown is True
