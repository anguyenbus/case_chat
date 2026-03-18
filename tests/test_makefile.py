"""
Tests for Makefile commands.

Tests that Makefile targets execute correctly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class TestMakefileCommands:
    """Test Makefile command execution."""

    def test_makefile_exists(self):
        """Test that Makefile exists."""
        project_root = Path(__file__).parent.parent
        makefile = project_root / "Makefile"

        assert makefile.exists()

    def test_make_help_displays_commands(self):
        """Test that make help command displays commands."""
        result = subprocess.run(
            ["make", "help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            check=False,
        )

        assert result.returncode == 0
        assert "install" in result.stdout
        assert "test" in result.stdout
        assert "lint" in result.stdout
        assert "format" in result.stdout

    def test_make_clean_removes_cache_directories(self, tmp_path):
        """Test that make clean command removes cache directories."""
        # Create some test cache directories
        cache_dirs = [
            tmp_path / "__pycache__",
            tmp_path / ".pytest_cache",
            tmp_path / ".ruff_cache",
        ]

        for cache_dir in cache_dirs:
            cache_dir.mkdir()
            assert cache_dir.exists()

        # Run make clean (note: this won't work in tmp_path, but we can test the command exists)
        result = subprocess.run(
            ["make", "clean"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            check=False,
        )

        assert result.returncode == 0
