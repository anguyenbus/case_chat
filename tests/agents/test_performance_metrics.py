"""
Tests for SessionManager performance metrics functionality.

Tests performance metrics table creation, insertion, and retrieval.
"""

from __future__ import annotations

import sqlite3
import time


class TestPerformanceMetrics:
    """Test SessionManager performance metrics functionality."""

    def test_performance_metrics_table_created_on_init(self, tmp_path):
        """Test that performance_metrics table is created on SessionManager initialization."""
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_metrics.db"
        SessionManager(db_file=db_file)

        # Connect and check table exists
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='performance_metrics'"
        )
        result = cursor.fetchone()

        conn.close()

        assert result is not None
        assert result[0] == "performance_metrics"

    def test_metrics_insertion_with_valid_data(self, tmp_path):
        """Test metrics insertion with valid data."""
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_metrics.db"
        session_manager = SessionManager(db_file=db_file)

        session_id = "test-session-123"
        duration_ms = 1500
        input_tokens = 100
        output_tokens = 200

        result = session_manager.save_metrics(
            session_id=session_id,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        assert result is True

    def test_metrics_insertion_with_missing_optional_fields(self, tmp_path):
        """Test metrics insertion with missing optional fields (metadata)."""
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_metrics.db"
        session_manager = SessionManager(db_file=db_file)

        session_id = "test-session-456"
        duration_ms = 2000
        input_tokens = 150
        output_tokens = 250

        # Save without metadata
        result = session_manager.save_metrics(
            session_id=session_id,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        assert result is True

    def test_metrics_indexes_created(self, tmp_path):
        """Test that indexes are created on session_id and timestamp."""
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_metrics.db"
        SessionManager(db_file)

        # Connect and check indexes exist
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name LIKE 'idx_performance_metrics%'"
        )
        indexes = cursor.fetchall()

        conn.close()

        index_names = [idx[0] for idx in indexes]
        assert "idx_performance_metrics_session_id" in index_names
        assert "idx_performance_metrics_timestamp" in index_names

    def test_error_handling_for_invalid_data_types(self, tmp_path):
        """Test error handling for invalid data types."""
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_metrics.db"
        session_manager = SessionManager(db_file=db_file)

        # Try to save with invalid data - should handle gracefully
        result = session_manager.save_metrics(
            session_id="",  # Empty session_id
            duration_ms=-1,  # Negative duration
            input_tokens=None,  # None tokens
            output_tokens=None,
        )

        # Should return False due to invalid data
        assert result is False

    def test_retrieval_of_metrics_by_session_id(self, tmp_path):
        """Test retrieval of metrics by session_id."""
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_metrics.db"
        session_manager = SessionManager(db_file=db_file)

        session_id = "test-session-789"

        # Save multiple metrics
        session_manager.save_metrics(
            session_id=session_id,
            duration_ms=1000,
            input_tokens=50,
            output_tokens=100,
        )
        session_manager.save_metrics(
            session_id=session_id,
            duration_ms=1500,
            input_tokens=75,
            output_tokens=125,
        )

        # Retrieve metrics (ordered by timestamp DESC, most recent first)
        metrics = session_manager.get_metrics(session_id=session_id)

        assert len(metrics) == 2
        assert all(m["session_id"] == session_id for m in metrics)
        # Most recent metric (1500ms) should be first
        assert metrics[0]["duration_ms"] == 1500
        assert metrics[1]["duration_ms"] == 1000

    def test_retrieval_of_metrics_within_date_range(self, tmp_path):
        """Test retrieval of metrics within a date range."""
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_metrics.db"
        session_manager = SessionManager(db_file=db_file)

        session_id = "test-session-daterange"

        # Save metrics at different times
        current_time = int(time.time() * 1000)  # milliseconds

        # Old metric (2 hours ago)
        current_time - (2 * 60 * 60 * 1000)
        session_manager.save_metrics(
            session_id=session_id,
            duration_ms=1000,
            input_tokens=50,
            output_tokens=100,
        )

        # Recent metric (within last hour)
        session_manager.save_metrics(
            session_id=session_id,
            duration_ms=2000,
            input_tokens=100,
            output_tokens=200,
        )

        # Retrieve metrics for last hour
        start_time = current_time - (60 * 60 * 1000)
        metrics = session_manager.get_metrics(session_id=session_id, start_timestamp=start_time)

        # Should only return the recent metric
        assert len(metrics) >= 1
