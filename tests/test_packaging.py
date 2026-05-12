"""Tests for the public package name and console entry points."""

import tomllib
from pathlib import Path


def test_project_uses_agent_sandbox_package_identity() -> None:
    """Verify packaging metadata matches the renamed sandbox provider."""

    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["name"] == "agent-sandbox"
    assert data["project"]["license"] == "MIT"
    assert data["project"]["scripts"] == {
        "agent-sandbox": "agent_sandbox.cli.sandbox:main",
        "agent-sandbox-python": "agent_sandbox.cli.python:main",
        "agent-sandbox-screenshot": "agent_sandbox.cli.screenshot:main",
        "agent-sandbox-shell": "agent_sandbox.cli.shell:main",
    }


def test_public_package_exports_sdk_and_registry() -> None:
    """Verify the stable package surface includes the registry adapter."""

    import agent_sandbox

    assert agent_sandbox.__all__ == [
        "SandboxToolPolicy",
        "SandboxToolExecutor",
        "SandboxToolRegistry",
        "SandboxTools",
        "ToolCall",
        "ToolResult",
        "ToolSpec",
        "create_fake_sandbox_tools",
    ]
