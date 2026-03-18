"""
Tests for project configuration.

Tests project structure and pyproject.toml configuration.
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestProjectConfiguration:
    """Test project configuration and structure."""

    def test_pyproject_toml_exists(self):
        """Test that pyproject.toml exists in project root."""
        project_root = Path(__file__).parent.parent
        pyproject_path = project_root / "pyproject.toml"
        assert pyproject_path.exists(), "pyproject.toml must exist in project root"

    def test_pyproject_toml_is_valid(self):
        """Test that pyproject.toml is valid TOML."""
        project_root = Path(__file__).parent.parent
        pyproject_path = project_root / "pyproject.toml"

        try:
            import tomllib

            with pyproject_path.open("rb") as f:
                config = tomllib.load(f)
            assert config is not None
            assert "project" in config
            assert config["project"]["name"] == "case-chat"
        except Exception as e:
            pytest.fail(f"pyproject.toml is not valid TOML: {e}")

    def test_src_directory_exists(self):
        """Test that src/case_chat directory exists."""
        src_path = Path(__file__).parent.parent / "src" / "case_chat"
        assert src_path.exists(), "src/case_chat directory must exist"
        assert src_path.is_dir(), "src/case_chat must be a directory"

    def test_tests_directory_exists(self):
        """Test that tests directory exists."""
        tests_path = Path(__file__).parent.parent / "tests"
        assert tests_path.exists(), "tests directory must exist"
        assert tests_path.is_dir(), "tests must be a directory"

    def test_examples_directory_exists(self):
        """Test that examples directory exists."""
        examples_path = Path(__file__).parent.parent / "examples"
        assert examples_path.exists(), "examples directory must exist"
        assert examples_path.is_dir(), "examples must be a directory"

    def test_package_init_exists(self):
        """Test that src/case_chat/__init__.py exists."""
        init_path = Path(__file__).parent.parent / "src" / "case_chat" / "__init__.py"
        assert init_path.exists(), "src/case_chat/__init__.py must exist"

    def test_package_metadata(self):
        """Test that package has correct metadata."""
        import case_chat

        assert hasattr(case_chat, "__version__")
        assert case_chat.__version__ == "0.1.0"
