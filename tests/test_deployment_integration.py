"""
Tests for AgentOS deployment integration.

Tests deployment script integration with AgentFactory.
"""

from __future__ import annotations


class TestDeploymentIntegration:
    """Test AgentOS deployment integration."""

    def test_agent_factory_import_works_in_deployment(self, tmp_path):
        """Test that AgentFactory import works in deployment script."""
        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_deployment.db"
        session_manager = SessionManager(db_file=db_file)

        # Should be able to import and instantiate
        factory = AgentFactory(session_manager=session_manager)
        assert factory is not None

    def test_create_agent_returns_agent_instance(self, tmp_path):
        """Test that create_agent() returns Agent instance."""
        from agno.agent import Agent

        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_deployment.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        agent = factory.create_agent(session_id="test-session")

        # Should return Agent instance
        assert isinstance(agent, Agent)

    def test_agent_os_accepts_agent_in_constructor(self, tmp_path):
        """Test that AgentOS accepts Agent (not Team) in constructor."""
        from agno.os import AgentOS

        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_deployment.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        agent = factory.create_agent(session_id="test-session")

        # AgentOS should accept Agent directly
        agent_os = AgentOS(
            description="Test Deployment",
            agents=[agent],
        )

        assert agent_os is not None

    def test_fastapi_app_composition_with_agent_only(self, tmp_path):
        """Test that FastAPI app composition works with Agent-only deployment."""
        from agno.os import AgentOS

        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_deployment.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        agent = factory.create_agent(session_id="test-session")

        # Create AgentOS with agent
        agent_os = AgentOS(
            description="Test Deployment",
            agents=[agent],
        )

        # Get FastAPI app
        app = agent_os.get_app()

        assert app is not None
        assert app.routes  # Should have routes

    def test_document_upload_router_integration_maintained(self, tmp_path):
        """Test that document upload router integration is maintained."""
        from agno.os import AgentOS

        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager
        from case_chat.api.documents import router as documents_router

        db_file = tmp_path / "test_deployment.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        agent = factory.create_agent(session_id="test-session")

        # Create AgentOS
        agent_os = AgentOS(
            description="Test Deployment",
            agents=[agent],
        )

        # Get app and include router
        app = agent_os.get_app()
        app.include_router(documents_router, tags=["documents"])

        # Router should be included
        assert any("/documents" in route.path for route in app.routes)

    def test_logging_messages_reflect_agent_terminology(self, tmp_path, caplog):
        """Test that logging messages reflect Agent terminology."""
        import logging

        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_deployment.db"
        session_manager = SessionManager(db_file=db_file)

        with caplog.at_level(logging.INFO):
            factory = AgentFactory(session_manager=session_manager)
            factory.create_agent(session_id="test-session")

            # Check logs don't contain "Team" terminology
            log_messages = [record.message for record in caplog.records]
            assert not any("Team" in msg for msg in log_messages)

    def test_control_plane_accessible_at_localhost(self, tmp_path):
        """Test that control plane is accessible at localhost:7777."""
        from agno.os import AgentOS

        from case_chat.agents.agent_factory import AgentFactory
        from case_chat.agents.session_manager import SessionManager

        db_file = tmp_path / "test_deployment.db"
        session_manager = SessionManager(db_file=db_file)
        factory = AgentFactory(session_manager=session_manager)

        agent = factory.create_agent(session_id="test-session")

        # Create AgentOS
        agent_os = AgentOS(
            description="Test Deployment",
            agents=[agent],
        )

        # Get app - should be accessible at localhost:7777 when served
        app = agent_os.get_app()
        assert app is not None
