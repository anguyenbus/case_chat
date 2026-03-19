"""
Case Chat - AgentOS Deployment Example.

This example demonstrates how to deploy your Case Chat agents to AgentOS
for testing on os.agno.com or via the local control plane at localhost:7777.

Prerequisites:
1. uv sync --all-extras --dev
2. API key configured in .env file (z_api_key)
3. MLflow server running for tracing (optional but recommended)

Usage:
    # Local testing with control plane at http://localhost:7777
    uv run python examples/case_chat_agentos_deploy.py

    # After starting, visit http://localhost:7777 to chat with your agents

MLflow Setup (for tracing):
    # Start MLflow server
    mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlflow-artifacts

    # Configure .env file
    MLFLOW_TRACKING_URI=http://localhost:5000
    MLFLOW_EXPERIMENT_NAME=case-chat-agent
"""

from __future__ import annotations

import logging
from pathlib import Path

from agno.os import AgentOS
from dotenv import load_dotenv

# NOTE: Load environment before other case_chat imports
load_dotenv()

from case_chat.agents.agent_factory import AgentFactory  # noqa: E402
from case_chat.agents.session_manager import SessionManager  # noqa: E402
from case_chat.api.documents import router as documents_router  # noqa: E402
from case_chat.config import get_app_settings  # noqa: E402

# Configure logging - NO EMOJIS, use tags instead
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Initialize and serve the Case Chat AgentOS instance."""
    logger.info("=== Case Chat AgentOS Deployment ===")

    # Get configuration
    settings = get_app_settings()

    logger.info("Environment: %s", settings.environment)
    logger.info("Log Level: %s", settings.log_level)
    logger.info("Model ID: %s", settings.model_id)

    # Create tmp directory for database
    Path("tmp").mkdir(exist_ok=True)

    # Create session manager for conversation persistence
    session_manager = SessionManager(
        db_file=Path("tmp/case_chat.db"),
        session_table="agent_sessions",
    )

    logger.info("[SETUP] SessionManager initialized: db_path=tmp/case_chat.db")

    # Initialize MLflow tracing
    try:
        from case_chat.observability.mlflow_config import (
            get_mlflow_settings,
        )
        from case_chat.observability.mlflow_tracing import (
            initialize_mlflow_tracing,
        )

        mlflow_settings = get_mlflow_settings()
        initialize_mlflow_tracing(mlflow_settings)

        # Log MLflow configuration
        logger.info("[MLFLOW] MLflow tracing enabled")
        logger.info("[MLFLOW] View traces: %s/#/experiments/", mlflow_settings.tracking_uri)
        logger.info("[MLFLOW] Tracing scope: model calls, tools, RAG operations, document uploads")

    except Exception as e:
        logger.warning("[MLFLOW] MLflow tracing not available: %s", e)
        logger.info("[MLFLOW] Proceeding without MLflow tracing")

    # Create agent factory with session support
    factory = AgentFactory(session_manager=session_manager)

    # Create the Case Chat Agent
    agent = factory.create_agent(session_id="agentos-demo")

    logger.info("[AGENT] Created Case Chat Agent")
    logger.info("[AGENT] Agent: case-chat-assistant")
    logger.info("[AGENT] Session History Limit: 3 conversation turns")
    logger.info("[AGENT] Instructions: Tax law case analysis")

    # Create AgentOS instance with agent
    agent_os = AgentOS(
        description="Case Chat - Tax Law Case Analysis",
        agents=[agent],
        cors_allowed_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    )

    # Get the FastAPI app
    app = agent_os.get_app()

    # Add CORS middleware to allow requests from frontend
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:8080",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info(
        "[CORS] Configured to allow requests from localhost:3000, localhost:3001, localhost:8080"
    )

    # Include document upload router
    app.include_router(documents_router, tags=["documents"])

    logger.info("[API] Included document upload endpoints")

    logger.info("")
    logger.info("=== AgentOS Ready ===")
    logger.info("Control Plane: http://localhost:7777")
    logger.info("API Docs: http://localhost:7777/docs")
    logger.info("Health Check: http://localhost:7777/health")
    logger.info("")
    logger.info("Press Ctrl+C to stop the server")
    logger.info("")

    # Serve the AgentOS instance
    # Note: reload=False required when passing app object directly
    agent_os.serve(app=app, reload=False, port=7777)


if __name__ == "__main__":
    main()
