"""Tests for one-shot CLI commands and their JSON output."""

import json
from pathlib import Path

from agent_sandbox import ToolResult
from agent_sandbox.cli import python as python_cli
from agent_sandbox.cli import screenshot as screenshot_cli
from agent_sandbox.cli import shell as shell_cli


class FakeTools:
    """Small SandboxTools stand-in for CLI tests."""

    init_kwargs: dict[str, object] = {}

    def __init__(self, **kwargs: object) -> None:
        """Record constructor options passed by a CLI command.

        Args:
            **kwargs: Keyword arguments used to build SandboxTools.
        """

        type(self).init_kwargs = kwargs

    def shell(self, command: list[str]) -> ToolResult:
        """Return a fake shell result.

        Args:
            command: Command words parsed by the CLI.

        Returns:
            Structured fake result for CLI printing.
        """

        return ToolResult(
            status="succeeded",
            returncode=0,
            stdout="shell ok\n",
            metadata={"tool": "shell", "command": command},
        )

    def python_script(self, script_path: Path, *args: str) -> ToolResult:
        """Return a fake Python result.

        Args:
            script_path: Script path parsed by the CLI.
            *args: Extra script arguments parsed by the CLI.

        Returns:
            Structured fake result for CLI printing.
        """

        return ToolResult(
            status="succeeded",
            returncode=0,
            stdout="python ok\n",
            metadata={
                "tool": "python",
                "script_path": str(script_path),
                "args": list(args),
            },
        )

    def screenshot(self, url: str) -> ToolResult:
        """Return a fake screenshot result.

        Args:
            url: Resolved URL parsed by the CLI.

        Returns:
            Structured fake result for CLI printing.
        """

        return ToolResult(
            status="succeeded",
            returncode=0,
            metadata={
                "tool": "browser",
                "url": url,
                "image_path": "artifacts/example.png",
                "text_path": "artifacts/example.txt",
            },
        )


def test_shell_cli_prints_json(monkeypatch, capsys) -> None:
    """Verify agent-sandbox-shell can emit ToolResult JSON."""

    monkeypatch.setattr(shell_cli, "SandboxTools", FakeTools)

    result = shell_cli.main(["--json", "--record-run", "--", "python", "--version"])

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload["stdout"] == "shell ok\n"
    assert payload["metadata"]["command"] == ["python", "--version"]
    assert FakeTools.init_kwargs["record_runs"] is True


def test_python_cli_prints_json(monkeypatch, capsys) -> None:
    """Verify agent-sandbox-python can emit ToolResult JSON."""

    monkeypatch.setattr(python_cli, "SandboxTools", FakeTools)

    result = python_cli.main(["--json", "script.py", "arg"])

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload["stdout"] == "python ok\n"
    assert payload["metadata"]["script_path"] == "script.py"
    assert payload["metadata"]["args"] == ["arg"]


def test_screenshot_cli_prints_json(monkeypatch, capsys) -> None:
    """Verify agent-sandbox-screenshot can emit ToolResult JSON."""

    monkeypatch.setattr(screenshot_cli, "SandboxTools", FakeTools)

    result = screenshot_cli.main(["--json", "https://example.com"])

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload["metadata"]["url"] == "https://example.com"
    assert payload["metadata"]["image_path"] == "artifacts/example.png"
