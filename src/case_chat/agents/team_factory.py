"""
Team factory for creating Agno Teams.

This module provides factory functions for creating Agno Team instances
configured with agents for tax law case analysis.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agno.agent import Agent

from case_chat.config import get_app_settings

if TYPE_CHECKING:
    from case_chat.agents.session_manager import SessionManager

logger = logging.getLogger(__name__)


class TeamFactory:
    """
    Factory for creating Agno Teams with agents.

    This class creates team instances configured with
    agents for tax law case analysis.

    Attributes
    ----------
    _session_manager : SessionManager
        The session manager for conversation persistence

    """

    __slots__ = ("_session_manager",)

    def __init__(self, session_manager: SessionManager):
        """
        Initialize the TeamFactory.

        Parameters
        ----------
        session_manager : SessionManager
            The session manager for conversation persistence

        Examples
        --------
        >>> from case_chat.agents.session_manager import SessionManager
        >>> factory = TeamFactory(session_manager=SessionManager())
        >>> team = factory.create_team(session_id="user-123")

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

    def create_team(self, session_id: str = "default"):
        """
        Create a Agno Team with agents.

        Parameters
        ----------
        session_id : str
            Session ID for conversation tracking

        Returns
        -------
        Team or Agent
            Configured Agno Team instance or Agent

        Examples
        --------
        >>> factory = TeamFactory(session_manager=SessionManager())
        >>> team = factory.create_team(session_id="user-123")

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

        # Create the agent
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
            session_id=session_id,
        )

        logger.info(f"Created agent 'case-chat-assistant' for session {session_id}")

        # Create a simple team with the agent
        try:
            from agno.team import Team

            team = Team(
                name="case-chat-team",
                members=[agent],
                session_id=session_id,
            )

            logger.info(f"Created team 'case-chat-team' for session {session_id}")

            return team

        except ImportError:
            # If Team is not available, return the agent directly
            # (for compatibility with older Agno versions)
            logger.warning("Team not available, returning agent directly")
            return agent
