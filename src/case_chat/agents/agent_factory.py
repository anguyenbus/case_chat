"""
Agent factory for creating Agno Agents.

This module provides factory functions for creating Agno Agent instances
configured for tax law case analysis.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agno.agent import Agent

from case_chat.config import get_app_settings

if TYPE_CHECKING:
    from case_chat.agents.session_manager import SessionManager

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Factory for creating Agno Agents.

    This class creates agent instances configured for
    tax law case analysis with session history limits
    to improve performance for long conversations.

    Attributes
    ----------
    _session_manager : SessionManager
        The session manager for conversation persistence

    """

    __slots__ = ("_session_manager",)

    def __init__(self, session_manager: SessionManager):
        """
        Initialize the AgentFactory.

        Parameters
        ----------
        session_manager : SessionManager
            The session manager for conversation persistence

        Examples
        --------
        >>> from case_chat.agents.session_manager import SessionManager
        >>> factory = AgentFactory(session_manager=SessionManager())
        >>> agent = factory.create_agent(session_id="user-123")

        """
        self._session_manager = session_manager

    @property
    def session_manager(self) -> SessionManager:
        """
        Get the session manager.

        Returns
        -------
        SessionManager
            The session manager for conversation persistence

        """
        return self._session_manager

    def create_agent(self, session_id: str = "default"):
        """
        Create a Agno Agent for tax law case analysis.

        Parameters
        ----------
        session_id : str
            Session ID for conversation tracking

        Returns
        -------
        Agent
            Configured Agno Agent instance with session history limits

        Examples
        --------
        >>> factory = AgentFactory(session_manager=SessionManager())
        >>> agent = factory.create_agent(session_id="user-123")

        """
        # Get application settings for model configuration
        settings = get_app_settings()

        # Create the model for GLM-5
        # Note: Using OpenAI-compatible interface for GLM models
        import os

        try:
            from agno.models.openai import OpenAIChat

            # Get Zhipu AI API key for OpenAI-compatible interface
            z_api_key = os.environ.get("z_api_key")
            if not z_api_key:
                logger.warning("[WARN] z_api_key not found in environment")

            model = OpenAIChat(
                id=settings.model_id,  # e.g., "glm-5"
                api_key=z_api_key,
                base_url="https://open.bigmodel.cn/api/paas/v4/",
            )
            logger.info(f"[SETUP] Created model {settings.model_id} with Zhipu AI endpoint")
        except ImportError:
            # Fallback if OpenAIChat is not available
            logger.warning("OpenAIChat not available, using default model")
            model = None

        # Create the agent with session history limits
        # num_history_runs=3 limits context to last 3 conversation turns
        # This reduces token usage and improves response time for long conversations
        agent = Agent(
            name="case-chat-assistant",
            model=model,
            instructions=[
                "You are a helpful assistant for tax law case analysis.",
                "Provide accurate and helpful information about tax law matters.",
                "Always cite relevant tax laws and regulations when possible.",
                "If you're unsure about something, acknowledge the limitations.",
                "Format your responses in markdown for better readability.",
            ],
            # Attach database for session persistence
            db=self._session_manager.db,
            # Enable markdown output
            markdown=True,
            # Limit session context to last 3 conversation turns
            # This reduces token usage by 30-40% for long conversations
            num_history_runs=3,
            session_id=session_id,
        )

        logger.info(
            f"Created agent 'case-chat-assistant' for session {session_id} with num_history_runs=3"
        )

        return agent
