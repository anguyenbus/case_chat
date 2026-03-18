"""
Tests for AgentOS deployment and FastAPI backend.

Tests deployment script and FastAPI app creation.
"""

from __future__ import annotations


class TestFastAPIBackend:
    """Test FastAPI backend configuration."""

    def test_fastapi_app_creation(self):
        """Test that FastAPI app is created in main.py."""
        from case_chat.main import app

        assert app is not None
        assert app.title == "Case Chat"

    def test_health_check_endpoint(self):
        """Test that health check endpoint returns 200."""
        from fastapi.testclient import TestClient

        from case_chat.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert "status" in response.json()


class TestAgentOSDeployment:
    """Test AgentOS deployment configuration."""

    def test_deployment_script_exists(self):
        """Test that deployment script exists."""
        from pathlib import Path

        project_root = Path(__file__).parent.parent
        deploy_script = project_root / "examples" / "case_chat_agentos_deploy.py"

        assert deploy_script.exists()

    def test_load_dotenv_called_before_imports(self):
        """Test that load_dotenv is called before imports."""
        # This is verified by checking the deployment script structure
        from pathlib import Path

        project_root = Path(__file__).parent.parent
        deploy_script = project_root / "examples" / "case_chat_agentos_deploy.py"

        content = deploy_script.read_text()

        # Check that load_dotenv is imported and called early
        assert "from dotenv import load_dotenv" in content
        assert "load_dotenv()" in content

        # Check that it's called before case_chat imports
        load_dotenv_pos = content.find("load_dotenv()")
        case_chat_import_pos = content.find("from case_chat")
        msg = "load_dotenv() should be called before case_chat imports"
        assert load_dotenv_pos < case_chat_import_pos, msg
