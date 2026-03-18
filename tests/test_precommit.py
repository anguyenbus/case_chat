"""
Tests for pre-commit configuration.

Tests pre-commit hooks setup and execution.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


class TestPrecommitConfiguration:
    """Test pre-commit configuration."""

    def test_precommit_config_exists(self):
        """Test that .pre-commit-config.yaml exists."""
        project_root = Path(__file__).parent.parent
        config_path = project_root / ".pre-commit-config.yaml"
        assert config_path.exists(), ".pre-commit-config.yaml must exist"

    def test_precommit_config_is_valid_yaml(self):
        """Test that .pre-commit-config.yaml is valid YAML."""
        project_root = Path(__file__).parent.parent
        config_path = project_root / ".pre-commit-config.yaml"

        try:
            with config_path.open("r") as f:
                config = yaml.safe_load(f)
            assert config is not None
            assert "repos" in config
        except Exception as e:
            pytest.fail(f".pre-commit-config.yaml is not valid YAML: {e}")

    def test_precommit_has_ruff_hook(self):
        """Test that pre-commit config has ruff hook."""
        project_root = Path(__file__).parent.parent
        config_path = project_root / ".pre-commit-config.yaml"

        with config_path.open("r") as f:
            config = yaml.safe_load(f)

        # Check for ruff repo
        ruff_repo = None
        for repo in config["repos"]:
            if "ruff-pre-commit" in repo.get("repo", ""):
                ruff_repo = repo
                break

        assert ruff_repo is not None, "Ruff pre-commit hook must be configured"
        assert len(ruff_repo.get("hooks", [])) > 0, "Ruff must have at least one hook"
