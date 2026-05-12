"""Tests for the public SandboxTools API used by external harnesses."""

from pathlib import Path

import pytest

from agent_sandbox import SandboxToolPolicy, SandboxTools
from agent_sandbox.sandbox.types import CommandResult


class FakeShellPrimitive:
    """Successful shell primitive used to test SDK result conversion."""

    def run(
        self,
        command: list[str],
        timeout: int | None = None,
        idle_timeout: int | None = None,
    ) -> CommandResult:
        """Return a successful command result without launching Modal.

        Args:
            command: Command words passed through the SDK.
            timeout: Optional timeout forwarded by the SDK.
            idle_timeout: Optional idle timeout forwarded by the SDK.

        Returns:
            A successful fake command result.
        """

        return CommandResult(returncode=0, stdout="ok\n", stderr="")


class FailingShellPrimitive:
    """Failing shell primitive used to test nonzero return codes."""

    def run(
        self,
        command: list[str],
        timeout: int | None = None,
        idle_timeout: int | None = None,
    ) -> CommandResult:
        """Return a failed command result without launching Modal.

        Args:
            command: Command words passed through the SDK.
            timeout: Optional timeout forwarded by the SDK.
            idle_timeout: Optional idle timeout forwarded by the SDK.

        Returns:
            A failed fake command result.
        """

        return CommandResult(returncode=2, stdout="", stderr="bad\n")


class FakeBrowserPrimitive:
    """Browser primitive that writes fake screenshot artifacts locally."""

    def capture_page(self, url: str, image_path: Path, text_path: Path) -> None:
        """Create fake files where the real browser primitive would write.

        Args:
            url: URL the SDK requested.
            image_path: Local screenshot output path.
            text_path: Local observation output path.
        """

        image_path.write_bytes(b"png")
        text_path.write_text("notes", encoding="utf-8")


def test_sandbox_tools_returns_structured_shell_result() -> None:
    """Verify shell calls return the public structured result shape."""

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
    """Verify nonzero command return codes become failed tool results."""

    tools = SandboxTools(
        policy=SandboxToolPolicy(allowed_tools=("shell",)),
        shell_primitive=FailingShellPrimitive(),
    )

    result = tools.shell(["false"])

    assert result.status == "failed"
    assert result.returncode == 2
    assert result.stderr == "bad\n"


def test_sandbox_tools_rejects_disallowed_tools() -> None:
    """Verify the allowlist policy blocks tools the harness did not grant."""

    tools = SandboxTools(policy=SandboxToolPolicy(allowed_tools=("python",)))

    with pytest.raises(PermissionError, match="shell"):
        tools.shell(["python", "--version"])


def test_sandbox_tools_screenshot_returns_artifacts(tmp_path: Path) -> None:
    """Verify screenshot calls return artifact records and convenience paths.

    Args:
        tmp_path: Pytest-provided temporary directory for screenshot outputs.
    """

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
