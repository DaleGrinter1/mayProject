import tomllib
from pathlib import Path


def test_project_uses_agent_sandbox_package_identity() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["name"] == "agent-sandbox"
    assert data["project"]["scripts"] == {
        "agent-sandbox": "agent_sandbox.cli.sandbox:main",
        "agent-sandbox-python": "agent_sandbox.cli.python:main",
        "agent-sandbox-screenshot": "agent_sandbox.cli.screenshot:main",
        "agent-sandbox-shell": "agent_sandbox.cli.shell:main",
    }
