from pathlib import Path

from agent_sandbox.config import load_config


def test_load_config_uses_defaults_when_file_is_missing(tmp_path: Path) -> None:
    config = load_config(tmp_path / "missing.toml")

    assert config.app_name == "my-app"
    assert config.artifacts_dir == Path("artifacts")


def test_load_config_reads_agent_sandbox_settings(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
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
