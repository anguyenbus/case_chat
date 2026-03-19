#!/usr/bin/env python3
"""
MLflow Setup Verification Script.

This script verifies that MLflow tracing is properly configured and working.
It checks:
1. MLflow dependencies are installed
2. Environment variables are configured
3. MLflow server connectivity
4. MLflow configuration is valid
5. Tracing initialization works

Usage:
    python scripts/verify_mlflow_setup.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def check_mlflow_dependencies() -> bool:
    """Check if MLflow dependencies are installed."""
    print("[1/5] Checking MLflow dependencies...")

    dependencies = [
        ("mlflow", "mlflow"),
        ("openinference-instrumentation-agno", "openinference_instrumentation_agno"),
        ("opentelemetry-exporter-otlp", "opentelemetry_exporter_otlp"),
    ]

    missing = []
    for display_name, module_name in dependencies:
        if importlib.util.find_spec(module_name) is None:
            missing.append(display_name)
        else:
            print(f"  ✓ {display_name} installed")

    if missing:
        print(f"  ✗ Missing dependencies: {', '.join(missing)}")
        print("\n  Run: uv sync --all-extras --dev")
        return False

    return True


def check_environment_variables() -> bool:
    """Check if MLflow environment variables are configured."""
    print("\n[2/5] Checking environment variables...")

    import os

    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    experiment_name = os.environ.get("MLFLOW_EXPERIMENT_NAME")

    if not tracking_uri:
        print("  ✗ MLFLOW_TRACKING_URI not set")
        print("\n  Add to .env file:")
        print("  MLFLOW_TRACKING_URI=http://localhost:5000")
        return False

    if not experiment_name:
        print("  ✗ MLFLOW_EXPERIMENT_NAME not set")
        print("\n  Add to .env file:")
        print("  MLFLOW_EXPERIMENT_NAME=case-chat-agent")
        return False

    print(f"  ✓ MLFLOW_TRACKING_URI={tracking_uri}")
    print(f"  ✓ MLFLOW_EXPERIMENT_NAME={experiment_name}")
    return True


def check_mlflow_server_connectivity() -> bool:
    """Check if MLflow server is reachable."""
    print("\n[3/5] Checking MLflow server connectivity...")

    import os

    import requests

    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    health_url = f"{tracking_uri}/health"

    try:
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            print(f"  ✓ MLflow server is reachable at {tracking_uri}")
            return True
        else:
            print(f"  ✗ MLflow server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Cannot connect to MLflow server at {tracking_uri}")
        print("\n  Start MLflow server:")
        print("  make mlflow")
        print("  or")
        print(
            "  uv run mlflow server --backend-store-uri"
            " sqlite:///mlflow.db --default-artifact-root ./mlflow-artifacts"
        )
        return False
    except Exception as e:
        print(f"  ✗ Error checking MLflow server: {e}")
        return False


def check_mlflow_configuration() -> bool:
    """Check if MLflow configuration is valid."""
    print("\n[4/5] Checking MLflow configuration...")

    try:
        from case_chat.observability.mlflow_config import get_mlflow_settings

        settings = get_mlflow_settings()
        print("  ✓ MLflowSettings loaded successfully")
        print(f"    tracking_uri: {settings.tracking_uri}")
        print(f"    experiment_name: {settings.experiment_name}")
        return True
    except Exception as e:
        print(f"  ✗ Failed to load MLflow settings: {e}")
        return False


def check_mlflow_tracing_initialization() -> bool:
    """Check if MLflow tracing initialization works."""
    print("\n[5/5] Checking MLflow tracing initialization...")

    try:
        from case_chat.observability.mlflow_config import get_mlflow_settings
        from case_chat.observability.mlflow_tracing import initialize_mlflow_tracing

        settings = get_mlflow_settings()
        initialize_mlflow_tracing(settings)

        print("  ✓ MLflow tracing initialized successfully")
        print("  ✓ Agno autolog enabled - traces will be captured")
        return True
    except Exception as e:
        print(f"  ✗ Failed to initialize MLflow tracing: {e}")
        return False


def main() -> int:
    """Run all verification checks."""
    print("=" * 60)
    print("MLflow Setup Verification")
    print("=" * 60)

    # Add project root to Python path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv()

    # Run all checks
    results = {
        "Dependencies": check_mlflow_dependencies(),
        "Environment Variables": check_environment_variables(),
        "Server Connectivity": check_mlflow_server_connectivity(),
        "Configuration": check_mlflow_configuration(),
        "Tracing Initialization": check_mlflow_tracing_initialization(),
    }

    # Print summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    all_passed = True
    for check_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {check_name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓ All checks passed! MLflow tracing is ready.")
        print("\nNext steps:")
        print("1. Start MLflow server: make mlflow")
        print("2. Start AgentOS deployment: make dev-backend")
        print("3. Interact with the agent at http://localhost:7777")
        print("4. View traces at http://localhost:5000")
        return 0
    else:
        print("\n✗ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
