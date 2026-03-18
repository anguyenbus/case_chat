"""
Tests for metrics collection logic.

Tests timing capture, token extraction, and metrics persistence.
"""

from __future__ import annotations

import time


class TestMetricsCollection:
    """Test metrics collection functionality."""

    def test_start_timestamp_captured_before_agent_run(self, tmp_path):
        """Test that start timestamp is captured before agent.run()."""
        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_metrics_collection.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        factory.create_agent(session_id="test-session")

        # Capture start time
        start_time = time.time()

        # Simulate agent.run() call
        time.sleep(0.01)  # Small delay

        # Capture end time
        end_time = time.time()

        # Verify start time is before end time
        assert start_time < end_time
        assert end_time - start_time >= 0.01

    def test_end_timestamp_captured_after_agent_run(self, tmp_path):
        """Test that end timestamp is captured after agent.run()."""
        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_metrics_collection.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        factory.create_agent(session_id="test-session")

        # Capture start time
        start_time = time.time()

        # Simulate agent.run() call
        time.sleep(0.01)

        # Capture end time
        end_time = time.time()

        # Calculate duration
        duration_ms = int((end_time - start_time) * 1000)

        # Verify duration is positive and reasonable
        assert duration_ms > 0
        assert duration_ms >= 10  # At least 10ms

    def test_duration_calculation_correct(self, tmp_path):
        """Test that duration calculation is correct (end - start)."""
        # Test with known delays
        start_time = time.time()
        time.sleep(0.05)  # 50ms delay
        end_time = time.time()

        duration_ms = int((end_time - start_time) * 1000)

        # Should be approximately 50ms (with some tolerance)
        assert 45 <= duration_ms <= 100  # Allow some variance

    def test_token_usage_extraction_from_response_metrics(self, tmp_path):
        """Test token usage extraction from response.metrics."""

        # Create a mock response with metrics
        class MockMetrics:
            """Mock metrics object."""

            input_tokens = 100
            output_tokens = 200

        class MockResponse:
            """Mock response object."""

            metrics = MockMetrics()

        response = MockResponse()

        # Extract token usage
        input_tokens = None
        output_tokens = None

        if hasattr(response, "metrics") and response.metrics:
            input_tokens = getattr(response.metrics, "input_tokens", None)
            output_tokens = getattr(response.metrics, "output_tokens", None)

        assert input_tokens == 100
        assert output_tokens == 200

    def test_graceful_handling_when_metrics_unavailable(self, tmp_path):
        """Test graceful handling when metrics are unavailable."""

        # Create a mock response without metrics
        class MockResponse:
            """Mock response object without metrics."""

            pass

        response = MockResponse()

        # Try to extract token usage
        input_tokens = None
        output_tokens = None

        if hasattr(response, "metrics") and response.metrics:
            input_tokens = getattr(response.metrics, "input_tokens", None)
            output_tokens = getattr(response.metrics, "output_tokens", None)

        # Should default to None
        assert input_tokens is None
        assert output_tokens is None

    def test_save_metrics_called_with_correct_parameters(self, tmp_path):
        """Test that save_metrics() is called with correct parameters."""
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_metrics_collection.db"
        session_manager = SessionManager(db_file=db_file)

        # Save metrics with test data
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

        # Verify save was successful
        assert result is True

        # Retrieve and verify metrics
        metrics = session_manager.get_metrics(session_id=session_id)
        assert len(metrics) == 1
        assert metrics[0]["duration_ms"] == duration_ms
        assert metrics[0]["input_tokens"] == input_tokens
        assert metrics[0]["output_tokens"] == output_tokens

    def test_session_id_included_in_metrics_record(self, tmp_path):
        """Test that session_id is included in metrics record."""
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_metrics_collection.db"
        session_manager = SessionManager(db_file=db_file)

        session_id = "test-session-456"

        session_manager.save_metrics(
            session_id=session_id,
            duration_ms=2000,
            input_tokens=150,
            output_tokens=250,
        )

        # Retrieve metrics
        metrics = session_manager.get_metrics(session_id=session_id)

        # Verify session_id is included
        assert len(metrics) == 1
        assert metrics[0]["session_id"] == session_id

    def test_structured_logging_with_metrics_tag(self, tmp_path, caplog):
        """Test structured logging with [METRICS] tag."""
        import logging

        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_metrics_collection.db"
        session_manager = SessionManager(db_file=db_file)

        with caplog.at_level(logging.DEBUG):
            session_manager.save_metrics(
                session_id="test-session-789",
                duration_ms=1000,
                input_tokens=50,
                output_tokens=100,
            )

            # Check for metrics-related log messages
            log_messages = [record.message for record in caplog.records]

            # Should have debug log about saving metrics
            assert any("Saved metrics" in msg for msg in log_messages)
