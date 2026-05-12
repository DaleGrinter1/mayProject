from pathlib import Path

import pytest

from agent_sandbox import SandboxToolPolicy, SandboxTools
from agent_sandbox.sandbox.types import CommandResult


class FakeShellPrimitive:
    def run(
        self,
        command: list[str],
        timeout: int | None = None,
        idle_timeout: int | None = None,
    ) -> CommandResult:
        return CommandResult(returncode=0, stdout="ok\n", stderr="")


class FailingShellPrimitive:
    def run(
        self,
        command: list[str],
        timeout: int | None = None,
        idle_timeout: int | None = None,
    ) -> CommandResult:
        return CommandResult(returncode=2, stdout="", stderr="bad\n")


class FakeBrowserPrimitive:
    def capture_page(self, url: str, image_path: Path, text_path: Path) -> None:
        image_path.write_bytes(b"png")
        text_path.write_text("notes", encoding="utf-8")


def test_sandbox_tools_returns_structured_shell_result() -> None:
    tools = SandboxTools(
        policy=SandboxToolPolicy(allowed_tools=("shell",)),
        shell_primitive=FakeShellPrimitive(),
    )

    result = tools.shell(["python", "--version"])

    assert result.status == "succeeded"
    assert result.returncode == 0
    assert result.stdout == "ok\n"
    assert result.metadata == {
        "tool": "shell",
        "command": ["python", "--version"],
    }
    assert result.to_dict()["artifacts"] == []


def test_sandbox_tools_marks_nonzero_commands_failed() -> None:
    tools = SandboxTools(
        policy=SandboxToolPolicy(allowed_tools=("shell",)),
        shell_primitive=FailingShellPrimitive(),
    )

    result = tools.shell(["false"])

    assert result.status == "failed"
    assert result.returncode == 2
    assert result.stderr == "bad\n"


def test_sandbox_tools_rejects_disallowed_tools() -> None:
    tools = SandboxTools(policy=SandboxToolPolicy(allowed_tools=("python",)))

    with pytest.raises(PermissionError, match="shell"):
        tools.shell(["python", "--version"])


def test_sandbox_tools_screenshot_returns_artifacts(tmp_path: Path) -> None:
    tools = SandboxTools(
        policy=SandboxToolPolicy(allowed_tools=("browser",)),
        browser_primitive=FakeBrowserPrimitive(),
    )

    result = tools.screenshot("https://example.com", output_dir=tmp_path)

    assert result.status == "succeeded"
    assert result.returncode == 0
    assert result.image_path is not None
    assert result.text_path is not None
    assert result.image_path.exists()
    assert result.text_path.read_text(encoding="utf-8") == "notes"
    assert [artifact.name for artifact in result.artifacts] == [
        "screenshot",
        "observation",
    ]
