"""
Session manager for Agno SqliteDb integration.

Manages conversation persistence using Agno's SqliteDb for
session state management across interactions.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from agno.db.sqlite import SqliteDb

if TYPE_CHECKING:
    from collections.abc import Mapping

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
        self._ensure_metrics_table()

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

    def _ensure_metrics_table(self) -> None:
        """
        Ensure performance_metrics table exists in the database.

        Creates the performance_metrics table if it doesn't exist,
        along with appropriate indexes for efficient querying.

        """
        try:
            conn = sqlite3.connect(str(self._db_file))
            cursor = conn.cursor()

            # Create performance_metrics table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id VARCHAR(255) NOT NULL,
                    timestamp BIGINT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    total_tokens INTEGER,
                    metadata TEXT
                )
                """
            )

            # Create index on session_id for efficient lookups
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_performance_metrics_session_id
                ON performance_metrics(session_id)
                """
            )

            # Create index on timestamp for efficient time-based queries
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp
                ON performance_metrics(timestamp)
                """
            )

            conn.commit()
            conn.close()

            logger.info("Ensured performance_metrics table exists with indexes")

        except Exception as e:
            logger.error(f"Failed to create performance_metrics table: {e}")
            raise

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

    def save_metrics(
        self,
        session_id: str,
        duration_ms: int,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> bool:
        """
        Save performance metrics to the database.

        Parameters
        ----------
        session_id : str
            Session ID for the metrics
        duration_ms : int
            Duration of the query in milliseconds
        input_tokens : Optional[int]
            Number of input tokens consumed
        output_tokens : Optional[int]
            Number of output tokens generated
        metadata : Optional[Mapping[str, Any]]
            Additional metadata as a dictionary

        Returns
        -------
        bool
            True if metrics were saved successfully, False otherwise

        Examples
        --------
        >>> manager = SessionManager()
        >>> manager.save_metrics(
        ...     session_id="user-123", duration_ms=1500, input_tokens=100, output_tokens=200
        ... )
        True

        """
        try:
            # Validate inputs
            if not session_id or duration_ms < 0:
                logger.warning("Invalid metrics data: session_id empty or duration_ms negative")
                return False

            # Calculate total tokens
            total_tokens = None
            if input_tokens is not None and output_tokens is not None:
                total_tokens = input_tokens + output_tokens

            # Convert metadata to JSON string
            metadata_json = None
            if metadata:
                metadata_json = json.dumps(metadata)

            # Get current timestamp in milliseconds
            import time

            timestamp = int(time.time() * 1000)

            # Insert metrics
            conn = sqlite3.connect(str(self._db_file))
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO performance_metrics
                (session_id, timestamp, duration_ms, input_tokens, output_tokens,
                 total_tokens, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    timestamp,
                    duration_ms,
                    input_tokens,
                    output_tokens,
                    total_tokens,
                    metadata_json,
                ),
            )

            conn.commit()
            conn.close()

            logger.debug(
                f"Saved metrics for session {session_id}: {duration_ms}ms, "
                f"{input_tokens}+{output_tokens} tokens"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to save metrics for session {session_id}: {e}")
            return False

    def get_metrics(
        self,
        session_id: str,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve performance metrics for a session.

        Parameters
        ----------
        session_id : str
            Session ID to retrieve metrics for (supports prefix matching)
        start_timestamp : Optional[int]
            Start timestamp in milliseconds (exclusive filter)
        end_timestamp : Optional[int]
            End timestamp in milliseconds (exclusive filter)

        Returns
        -------
        list[dict[str, Any]]
            List of metric records with keys:
            id, session_id, timestamp, duration_ms, input_tokens,
            output_tokens, total_tokens, metadata

        Examples
        --------
        >>> manager = SessionManager()
        >>> metrics = manager.get_metrics(session_id="user-123")
        >>> for m in metrics:
        ...     print(f"{m['timestamp']}: {m['duration_ms']}ms")

        >>> # Get metrics for last hour
        >>> import time
        >>> one_hour_ago = int(time.time() * 1000) - (60 * 60 * 1000)
        >>> recent_metrics = manager.get_metrics(
        ...     session_id="user-123", start_timestamp=one_hour_ago
        ... )

        """
        metrics = []

        try:
            conn = sqlite3.connect(str(self._db_file))
            cursor = conn.cursor()

            # Build query with optional filters
            query = """
                SELECT id, session_id, timestamp, duration_ms,
                       input_tokens, output_tokens, total_tokens, metadata
                FROM performance_metrics
                WHERE session_id LIKE ?
            """
            params: list[Any] = [f"{session_id}%"]

            if start_timestamp is not None:
                query += " AND timestamp >= ?"
                params.append(start_timestamp)

            if end_timestamp is not None:
                query += " AND timestamp <= ?"
                params.append(end_timestamp)

            query += " ORDER BY timestamp DESC"

            cursor.execute(query, params)

            for row in cursor.fetchall():
                metric = {
                    "id": row[0],
                    "session_id": row[1],
                    "timestamp": row[2],
                    "duration_ms": row[3],
                    "input_tokens": row[4],
                    "output_tokens": row[5],
                    "total_tokens": row[6],
                    "metadata": json.loads(row[7]) if row[7] else None,
                }
                metrics.append(metric)

            conn.close()

        except Exception as e:
            logger.error(f"Failed to retrieve metrics for session {session_id}: {e}")

        return metrics

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
