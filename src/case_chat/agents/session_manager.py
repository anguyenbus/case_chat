"""
Session manager for Agno SqliteDb integration.

Manages conversation persistence using Agno's SqliteDb for
session state management across interactions.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

from agno.db.sqlite import SqliteDb

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages Agno SqliteDb for session persistence.

    This class provides a SqliteDb instance configured for
    Agno Agent session persistence. The database is created
    automatically at the specified path.

    Attributes
    ----------
    _db_file : Path
        Path to the SQLite database file
    _session_table : str
        Name of the sessions table
    _db : SqliteDb
        The Agno SqliteDb instance

    """

    __slots__ = ("_db_file", "_session_table", "_db")

    DEFAULT_DB_FILE: Final[Path] = Path("tmp/case_chat.db")
    DEFAULT_SESSION_TABLE: Final[str] = "agent_sessions"

    def __init__(
        self,
        db_file: Path | None = None,
        session_table: str | None = None,
    ):
        """
        Initialize the SessionManager.

        Parameters
        ----------
        db_file : Optional[Path]
            Path to the SQLite database file.
            Defaults to tmp/case_chat.db
        session_table : Optional[str]
            Name of the sessions table.
            Defaults to "agent_sessions"

        Examples
        --------
        >>> manager = SessionManager()
        >>> db = manager.db

        >>> custom_manager = SessionManager(
        ...     db_file=Path("/custom/path/sessions.db"), session_table="my_sessions"
        ... )

        """
        self._db_file = db_file or self.DEFAULT_DB_FILE
        self._session_table = session_table or self.DEFAULT_SESSION_TABLE
        self._db = self._create_db()

    def _create_db(self) -> SqliteDb:
        """
        Create SqliteDb instance.

        Ensures the parent directory exists before creating
        the database instance.

        Returns
        -------
        SqliteDb
            Configured Agno SqliteDb instance

        """
        # Ensure parent directory exists
        self._db_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Creating SqliteDb at {self._db_file} with table '{self._session_table}'")

        return SqliteDb(
            db_file=str(self._db_file),
            session_table=self._session_table,
        )

    @property
    def db(self) -> SqliteDb:
        """
        Get the SqliteDb instance.

        Returns
        -------
        SqliteDb
            The Agno SqliteDb instance for session persistence

        """
        return self._db

    @property
    def db_file(self) -> Path:
        """
        Get the database file path.

        Returns
        -------
        Path
            Path to the SQLite database file

        """
        return self._db_file

    @property
    def session_table(self) -> str:
        """
        Get the session table name.

        Returns
        -------
        str
            Name of the sessions table

        """
        return self._session_table

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from the database.

        This removes all session data including runs and history.
        Useful for clearing sessions with corrupted or problematic history.

        Parameters
        ----------
        session_id : str
            Session ID to delete (can be partial prefix for matching)

        Returns
        -------
        bool
            True if session was deleted, False if not found

        Examples
        --------
        >>> manager = SessionManager()
        >>> manager.delete_session("user-123")
        True

        >>> # Delete by prefix
        >>> manager.delete_session("762451cf")
        True

        """
        import sqlite3

        try:
            conn = sqlite3.connect(str(self._db_file))
            cursor = conn.cursor()

            # Delete from agent_sessions table (uses LIKE for prefix matching)
            cursor.execute(
                f"DELETE FROM {self._session_table} WHERE session_id LIKE ?",
                (f"{session_id}%",),
            )
            deleted = cursor.rowcount

            conn.commit()
            conn.close()

            if deleted > 0:
                logger.info(f"Deleted session {session_id} ({deleted} rows)")
            else:
                logger.debug(f"Session {session_id} not found for deletion")

            return deleted > 0

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def list_sessions(self) -> list[dict[str, str]]:
        """
        List all sessions in the database.

        Returns
        -------
        list[dict[str, str]]
            List of session info dictionaries with keys:
            session_id, created_at, updated_at

        Examples
        --------
        >>> manager = SessionManager()
        >>> sessions = manager.list_sessions()
        >>> for s in sessions:
        ...     print(f"{s['session_id']}: {s['updated_at']}")

        """
        import sqlite3

        sessions = []

        try:
            conn = sqlite3.connect(str(self._db_file))
            cursor = conn.cursor()

            cursor.execute(
                f"SELECT session_id, created_at, updated_at FROM {self._session_table} "
                f"ORDER BY updated_at DESC",
            )

            for row in cursor.fetchall():
                sessions.append(
                    {
                        "session_id": row[0],
                        "created_at": row[1],
                        "updated_at": row[2],
                    },
                )

            conn.close()

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")

        return sessions
