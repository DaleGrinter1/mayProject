"""Tests for the public SandboxTools API used by external harnesses."""

import json
from pathlib import Path

import pytest

from agent_sandbox import SandboxToolPolicy, SandboxTools, ToolResult
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


class RaisingShellPrimitive:
    """Shell primitive that raises to test normalized SDK errors."""

    def run(
        self,
        command: list[str],
        timeout: int | None = None,
        idle_timeout: int | None = None,
    ) -> CommandResult:
        raise RuntimeError("boom")


class FakePythonPrimitive:
    """Python primitive used to test script policy without launching Modal."""

    def run_code(self, code: str, *args: str) -> CommandResult:
        return CommandResult(returncode=0, stdout="code\n", stderr="")

    def run_script(self, script_path: Path, *args: str) -> CommandResult:
        return CommandResult(returncode=0, stdout=str(script_path), stderr="")


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


def test_tool_result_to_dict_is_public_contract() -> None:
    """Verify ToolResult serializes every stable public field."""

    result = ToolResult(
        status="succeeded",
        returncode=0,
        stdout="out",
        stderr="",
        metadata={"tool": "shell"},
        duration_ms=5,
        run_id="abc123",
        run_dir=Path(".agent-sandbox/runs/example"),
    )

    assert result.to_dict() == {
        "artifacts": [],
        "completed_at": None,
        "duration_ms": 5,
        "error_code": None,
        "error": None,
        "metadata": {"tool": "shell"},
        "returncode": 0,
        "run_dir": ".agent-sandbox/runs/example",
        "run_id": "abc123",
        "started_at": None,
        "status": "succeeded",
        "stderr": "",
        "stdout": "out",
    }


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
    assert result.error_code == "tool_failed"


def test_sandbox_tools_sets_error_code_for_tool_exceptions() -> None:
    """Verify raised primitive errors get a stable error code."""

    tools = SandboxTools(
        policy=SandboxToolPolicy(allowed_tools=("shell",)),
        shell_primitive=RaisingShellPrimitive(),
    )

    result = tools.shell(["python", "--version"])

    assert result.status == "failed"
    assert result.error == "boom"
    assert result.error_code == "tool_exception"


def test_sandbox_tools_rejects_disallowed_tools() -> None:
    """Verify the allowlist policy blocks tools the harness did not grant."""

    tools = SandboxTools(policy=SandboxToolPolicy(allowed_tools=("python",)))

    with pytest.raises(PermissionError, match="shell"):
        tools.shell(["python", "--version"])


def test_sandbox_tools_rejects_disallowed_shell_command() -> None:
    """Verify shell command allowlists are enforced before sandbox startup."""

    tools = SandboxTools(
        policy=SandboxToolPolicy(
            allowed_tools=("shell",),
            allowed_shell_commands=("python",),
        ),
        shell_primitive=FakeShellPrimitive(),
    )

    with pytest.raises(PermissionError, match="Shell command 'bash'"):
        tools.shell(["bash", "-lc", "echo no"])


def test_sandbox_tools_rejects_shell_timeout_above_policy() -> None:
    """Verify timeout limits are enforced before sandbox startup."""

    tools = SandboxTools(
        policy=SandboxToolPolicy(allowed_tools=("shell",), max_timeout=10),
        shell_primitive=FakeShellPrimitive(),
    )

    with pytest.raises(PermissionError, match="exceeds policy maximum"):
        tools.shell(["python", "--version"], timeout=30)


def test_sandbox_tools_rejects_disallowed_browser_domain() -> None:
    """Verify browser domain allowlists are enforced before sandbox startup."""

    tools = SandboxTools(
        policy=SandboxToolPolicy(
            allowed_tools=("browser",),
            allowed_browser_domains=("example.com",),
        ),
        browser_primitive=FakeBrowserPrimitive(),
    )

    with pytest.raises(PermissionError, match="not allowed"):
        tools.screenshot("https://openai.com")


def test_sandbox_tools_accepts_screenshot_policy_alias(tmp_path: Path) -> None:
    """Verify harnesses can grant screenshot instead of browser."""

    tools = SandboxTools(
        policy=SandboxToolPolicy(allowed_tools=("screenshot",)),
        browser_primitive=FakeBrowserPrimitive(),
    )

    result = tools.screenshot("https://example.com", output_dir=tmp_path)

    assert result.status == "succeeded"


def test_sandbox_tools_rejects_python_script_outside_allowed_roots(
    tmp_path: Path,
) -> None:
    """Verify Python script path restrictions are enforced."""

    allowed_root = tmp_path / "allowed"
    denied_root = tmp_path / "denied"
    allowed_root.mkdir()
    denied_root.mkdir()
    script_path = denied_root / "script.py"
    script_path.write_text("print('no')", encoding="utf-8")
    tools = SandboxTools(
        policy=SandboxToolPolicy(
            allowed_tools=("python",),
            allowed_python_script_roots=(str(allowed_root),),
        ),
        python_primitive=FakePythonPrimitive(),
    )

    with pytest.raises(PermissionError, match="outside allowed roots"):
        tools.python_script(script_path)


def test_sandbox_tools_accepts_python_script_inside_allowed_roots(
    tmp_path: Path,
) -> None:
    """Verify Python scripts inside allowed roots can run."""

    script_path = tmp_path / "script.py"
    script_path.write_text("print('yes')", encoding="utf-8")
    tools = SandboxTools(
        policy=SandboxToolPolicy(
            allowed_tools=("python",),
            allowed_python_script_roots=(str(tmp_path),),
        ),
        python_primitive=FakePythonPrimitive(),
    )

    result = tools.python_script(script_path)

    assert result.status == "succeeded"


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


def test_sandbox_tools_can_record_shell_runs(tmp_path: Path) -> None:
    """Verify optional run recording writes result and stream files.

    Args:
        tmp_path: Pytest-provided temporary directory for run outputs.
    """

    tools = SandboxTools(
        policy=SandboxToolPolicy(allowed_tools=("shell",)),
        shell_primitive=FakeShellPrimitive(),
        record_runs=True,
        run_root=tmp_path,
    )

    result = tools.shell(["python", "--version"])

    assert result.run_id is not None
    assert result.run_dir is not None
    assert result.started_at is not None
    assert result.completed_at is not None
    assert result.duration_ms is not None
    assert (result.run_dir / "stdout.txt").read_text(encoding="utf-8") == "ok\n"
    payload = json.loads((result.run_dir / "result.json").read_text(encoding="utf-8"))
    assert payload["run_id"] == result.run_id
    assert payload["status"] == "succeeded"
