"""
Tests for SessionManager.

Tests SQLite database session management.
"""

from __future__ import annotations


class TestSessionManager:
    """Test SessionManager for session persistence."""

    def test_session_manager_initialization(self, tmp_path):
        """Test SessionManager initialization with db_file path."""
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_sessions.db"
        manager = SessionManager(db_file=db_file)

        assert manager.db_file == db_file
        assert manager.session_table == "agent_sessions"

    def test_session_manager_creates_parent_directory(self, tmp_path):
        """Test that _create_db() creates parent directory."""
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "subdir" / "test_sessions.db"
        SessionManager(db_file=db_file)

        # Parent directory should be created
        assert db_file.parent.exists()
        assert db_file.parent.is_dir()

    def test_db_property_returns_sqlitedb_instance(self, tmp_path):
        """Test that db property returns SqliteDb instance."""
        from agno.db.sqlite import SqliteDb

        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_sessions.db"
        manager = SessionManager(db_file=db_file)

        assert isinstance(manager.db, SqliteDb)

    def test_delete_session_removes_session(self, tmp_path):
        """Test that delete_session() removes session from database."""
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_sessions.db"
        manager = SessionManager(db_file=db_file)

        # Add a test session
        import sqlite3

        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {manager.session_table} "
            "(session_id TEXT, created_at TEXT, updated_at TEXT)",
        )
        cursor.execute(
            f"INSERT INTO {manager.session_table} VALUES (?, datetime('now'), datetime('now'))",
            ("test-session-123",),
        )
        conn.commit()
        conn.close()

        # Delete the session
        result = manager.delete_session("test-session-123")

        assert result is True

    def test_list_sessions_returns_session_list(self, tmp_path):
        """Test that list_sessions() returns list of sessions."""
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_sessions.db"
        manager = SessionManager(db_file=db_file)

        # Add test sessions
        import sqlite3

        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {manager.session_table} "
            "(session_id TEXT, created_at TEXT, updated_at TEXT)",
        )
        cursor.execute(
            f"INSERT INTO {manager.session_table} VALUES (?, datetime('now'), datetime('now'))",
            ("test-session-1",),
        )
        cursor.execute(
            f"INSERT INTO {manager.session_table} VALUES (?, datetime('now'), datetime('now'))",
            ("test-session-2",),
        )
        conn.commit()
        conn.close()

        # List sessions
        sessions = manager.list_sessions()

        assert len(sessions) == 2
        assert sessions[0]["session_id"] in ["test-session-1", "test-session-2"]
        assert sessions[1]["session_id"] in ["test-session-1", "test-session-2"]
