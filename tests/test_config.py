"""Tests for reading agent-sandbox settings from pyproject.toml."""

from pathlib import Path

from agent_sandbox.config import load_config


def test_load_config_uses_defaults_when_file_is_missing(tmp_path: Path) -> None:
    """Verify missing config files fall back to safe project defaults.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated files.
    """

    config = load_config(tmp_path / "missing.toml")

    assert config.app_name == "my-app"
    assert config.artifacts_dir == Path("artifacts")


def test_load_config_reads_agent_sandbox_settings(tmp_path: Path) -> None:
    """Verify the project-specific tool table overrides default settings.

    Args:
        tmp_path: Pytest-provided temporary directory for isolated files.
    """

    pyproject = tmp_path / "pyproject.toml"
    # This mirrors the table users configure in the real project pyproject.
    pyproject.write_text(
        """
        [tool.agent-sandbox]
        app_name = "test-app"
        artifacts_dir = "local-artifacts"
        """,
        encoding="utf-8",
    )

    config = load_config(pyproject)

    assert config.app_name == "test-app"
    assert config.artifacts_dir == Path("local-artifacts")
