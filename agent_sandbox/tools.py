from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from time import time
from typing import Any, Protocol
from urllib.parse import urlparse

from agent_sandbox.primitives.browser import BrowserPrimitive
from agent_sandbox.primitives.python import PythonPrimitive
from agent_sandbox.primitives.shell import ShellPrimitive
from agent_sandbox.sandbox.results import (
    DEFAULT_RUN_ROOT,
    Artifact,
    SandboxRun,
    create_sandbox_run,
    utc_now,
)
from agent_sandbox.sandbox.types import CommandResult


class ShellTool(Protocol):
    def run(
        self,
        command: Sequence[str],
        timeout: int | None = None,
        idle_timeout: int | None = None,
    ) -> CommandResult: ...


class PythonTool(Protocol):
    def run_code(self, code: str, *args: str) -> CommandResult: ...

    def run_script(self, script_path: Path, *args: str) -> CommandResult: ...


class BrowserTool(Protocol):
    def capture_page(self, url: str, image_path: Path, text_path: Path) -> None: ...


def tool_screenshot_path(url: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    host = urlparse(url).netloc or "screenshot"
    safe_host = "".join(c if c.isalnum() or c in ".-" else "-" for c in host)
    return output_dir / f"{safe_host}-{int(time())}.png"


@dataclass(frozen=True)
class SandboxToolPolicy:
    """Declares which sandbox-backed tools a harness may call.

    Attributes:
        allowed_tools: Tool names the harness has granted. Supported names are
            `shell`, `python`, and `browser`.
        allowed_shell_commands: Optional executable names that shell calls may
            run. When empty, any shell command is allowed after `shell` is
            granted.
        allowed_browser_domains: Optional hostnames that browser calls may
            capture. When empty, any URL is allowed after `browser` is granted.
        max_timeout: Optional maximum timeout a tool call may request.
        max_idle_timeout: Optional maximum idle timeout a shell call may request.
    """

    allowed_tools: tuple[str, ...] = ()
    allowed_shell_commands: tuple[str, ...] = ()
    allowed_browser_domains: tuple[str, ...] = ()
    max_timeout: int | None = None
    max_idle_timeout: int | None = None

    def require(self, tool: str) -> None:
        if tool not in self.allowed_tools:
            allowed = ", ".join(self.allowed_tools) or "none"
            raise PermissionError(
                f"Sandbox tool '{tool}' is not allowed. Allowed tools: {allowed}."
            )

    def require_shell_command(self, command: Sequence[str]) -> None:
        self.require("shell")
        if not self.allowed_shell_commands:
            return
        executable = command[0] if command else ""
        if executable not in self.allowed_shell_commands:
            allowed = ", ".join(self.allowed_shell_commands)
            raise PermissionError(
                f"Shell command '{executable or '<empty>'}' is not allowed. "
                f"Allowed commands: {allowed}."
            )

    def require_browser_url(self, url: str) -> None:
        self.require("browser")
        if not self.allowed_browser_domains:
            return
        host = urlparse(url).hostname or ""
        if not any(
            host == domain or host.endswith(f".{domain}")
            for domain in self.allowed_browser_domains
        ):
            allowed = ", ".join(self.allowed_browser_domains)
            raise PermissionError(
                f"Browser URL host '{host or '<empty>'}' is not allowed. "
                f"Allowed domains: {allowed}."
            )

    def require_timeout(
        self,
        timeout: int | None,
        idle_timeout: int | None = None,
    ) -> None:
        if (
            timeout is not None
            and self.max_timeout is not None
            and timeout > self.max_timeout
        ):
            raise PermissionError(
                f"Timeout {timeout}s exceeds policy maximum {self.max_timeout}s."
            )
        if (
            idle_timeout is not None
            and self.max_idle_timeout is not None
            and idle_timeout > self.max_idle_timeout
        ):
            raise PermissionError(
                "Idle timeout "
                f"{idle_timeout}s exceeds policy maximum {self.max_idle_timeout}s."
            )


@dataclass(frozen=True)
class ToolResult:
    """Structured result returned by harness-facing sandbox tools.

    Attributes:
        status: `succeeded` or `failed`.
        returncode: Process return code when a tool ran a command.
        stdout: Standard output captured from command-style tools.
        stderr: Standard error captured from command-style tools.
        artifacts: Files produced by the tool call.
        metadata: JSON-friendly details such as the tool name and inputs.
        error: Error message for failed tool setup or execution.
        run_id: Optional recorded run ID when run recording is enabled.
        started_at: UTC timestamp for when the tool call started.
        completed_at: UTC timestamp for when the tool call finished.
        duration_ms: Tool call duration in milliseconds.
        run_dir: Optional local run directory when run recording is enabled.
    """

    status: str
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    artifacts: tuple[Artifact, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    run_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    run_dir: Path | None = None

    @property
    def image_path(self) -> Path | None:
        value = self.metadata.get("image_path")
        return Path(value) if isinstance(value, str) else None

    @property
    def text_path(self) -> Path | None:
        value = self.metadata.get("text_path")
        return Path(value) if isinstance(value, str) else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "metadata": dict(self.metadata),
            "error": self.error,
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "run_dir": str(self.run_dir) if self.run_dir else None,
        }


@dataclass(frozen=True)
class SandboxTools:
    """Stable tool-provider API for external agent harnesses.

    Attributes:
        app_name: Modal app name used by default primitives.
        policy: Allowlist that decides which tools may run.
        artifact_dir: Base directory for screenshot outputs when run recording
            is disabled.
        record_runs: Whether to write per-call result files under `run_root`.
        run_root: Base directory for optional recorded run folders.
        shell_primitive: Optional injected shell primitive for tests/custom use.
        python_primitive: Optional injected Python primitive for tests/custom use.
        browser_primitive: Optional injected browser primitive for tests/custom use.
    """

    app_name: str = "my-app"
    policy: SandboxToolPolicy = SandboxToolPolicy()
    artifact_dir: Path = Path("artifacts/agents")
    record_runs: bool = False
    run_root: Path = DEFAULT_RUN_ROOT
    shell_primitive: ShellTool | None = None
    python_primitive: PythonTool | None = None
    browser_primitive: BrowserTool | None = None

    def shell(
        self,
        command: Sequence[str],
        timeout: int | None = None,
        idle_timeout: int | None = None,
    ) -> ToolResult:
        """Runs a shell command in a temporary per-task sandbox.

        Args:
            command: Command words to execute remotely.
            timeout: Optional maximum sandbox lifetime for this call.
            idle_timeout: Optional idle timeout for this call.

        Returns:
            Structured result containing stdout, stderr, return code, and
            timing/run metadata.
        """

        self.policy.require_shell_command(command)
        self.policy.require_timeout(timeout, idle_timeout)
        run = self._create_run("shell", {"command": list(command)})
        started_at = run.started_at if run else utc_now()
        primitive = self.shell_primitive or ShellPrimitive(app_name=self.app_name)
        try:
            result = primitive.run(command, timeout=timeout, idle_timeout=idle_timeout)
        except Exception as exc:
            return self._complete_result(
                ToolResult(
                    status="failed",
                    error=str(exc),
                    metadata={"tool": "shell", "command": list(command)},
                    started_at=started_at,
                ),
                run,
            )
        return self._complete_result(
            self._from_command(
                "shell",
                result,
                {"command": list(command)},
                started_at=started_at,
            ),
            run,
        )

    def python_code(self, code: str, *args: str) -> ToolResult:
        """Runs Python code in a temporary per-task sandbox.

        Args:
            code: Python source text to execute remotely.
            *args: Arguments passed to the remote Python script.

        Returns:
            Structured result containing stdout, stderr, return code, and
            timing/run metadata.
        """

        self.policy.require("python")
        metadata = {"args": list(args), "source": "code"}
        run = self._create_run("python", metadata)
        started_at = run.started_at if run else utc_now()
        primitive = self.python_primitive or PythonPrimitive(app_name=self.app_name)
        try:
            result = primitive.run_code(code, *args)
        except Exception as exc:
            return self._complete_result(
                ToolResult(
                    status="failed",
                    error=str(exc),
                    metadata={"tool": "python", **metadata},
                    started_at=started_at,
                ),
                run,
            )
        return self._complete_result(
            self._from_command("python", result, metadata, started_at=started_at),
            run,
        )

    def python_script(self, script_path: Path, *args: str) -> ToolResult:
        """Runs a local Python script in a temporary per-task sandbox.

        Args:
            script_path: Local Python script to copy into the sandbox.
            *args: Arguments passed to the remote Python script.

        Returns:
            Structured result containing stdout, stderr, return code, and
            timing/run metadata.
        """

        self.policy.require("python")
        metadata = {
            "args": list(args),
            "script_path": str(script_path),
            "source": "script",
        }
        run = self._create_run("python", metadata)
        started_at = run.started_at if run else utc_now()
        primitive = self.python_primitive or PythonPrimitive(app_name=self.app_name)
        try:
            result = primitive.run_script(script_path, *args)
        except Exception as exc:
            return self._complete_result(
                ToolResult(
                    status="failed",
                    error=str(exc),
                    metadata={"tool": "python", **metadata},
                    started_at=started_at,
                ),
                run,
            )
        return self._complete_result(
            self._from_command("python", result, metadata, started_at=started_at),
            run,
        )

    def screenshot(
        self,
        url: str,
        output_dir: Path | None = None,
    ) -> ToolResult:
        """Captures a web page in a temporary browser sandbox.

        Args:
            url: Web page URL to capture.
            output_dir: Optional local output directory for screenshot files.

        Returns:
            Structured result with screenshot and observation artifacts.
        """

        self.policy.require_browser_url(url)
        run = self._create_run("browser", {"url": url})
        started_at = run.started_at if run else utc_now()
        target_dir = output_dir or (
            run.artifact_dir / "artifacts" if run else self.artifact_dir / "screenshots"
        )
        image_path = tool_screenshot_path(url, target_dir)
        text_path = image_path.with_suffix(".txt")
        primitive = self.browser_primitive or BrowserPrimitive(app_name=self.app_name)
        try:
            primitive.capture_page(url, image_path, text_path)
        except Exception as exc:
            return self._complete_result(
                ToolResult(
                    status="failed",
                    metadata={
                        "tool": "browser",
                        "url": url,
                        "image_path": str(image_path),
                        "text_path": str(text_path),
                    },
                    error=str(exc),
                    started_at=started_at,
                ),
                run,
            )

        artifacts = (
            Artifact("screenshot", "image", image_path, "image/png"),
            Artifact("observation", "text", text_path, "text/plain"),
        )
        return self._complete_result(
            ToolResult(
                status="succeeded",
                returncode=0,
                artifacts=artifacts,
                metadata={
                    "tool": "browser",
                    "url": url,
                    "image_path": str(image_path),
                    "text_path": str(text_path),
                },
                started_at=started_at,
            ),
            run,
        )

    def _from_command(
        self,
        tool: str,
        result: CommandResult,
        metadata: dict[str, Any],
        started_at: datetime,
    ) -> ToolResult:
        return ToolResult(
            status="succeeded" if result.returncode == 0 else "failed",
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            metadata={"tool": tool, **metadata},
            started_at=started_at,
        )

    def _create_run(self, tool: str, metadata: dict[str, Any]) -> SandboxRun | None:
        if not self.record_runs:
            return None
        return create_sandbox_run(
            tool,
            run_root=self.run_root,
            tags={"tool": tool},
            metadata=metadata,
        )

    def _complete_result(self, result: ToolResult, run: SandboxRun | None) -> ToolResult:
        completed_at = utc_now()
        started_at = result.started_at or completed_at
        duration_ms = max(
            0,
            int((completed_at - started_at).total_seconds() * 1000),
        )
        completed_run = run.complete(result.status, completed_at) if run else None
        final = ToolResult(
            status=result.status,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            artifacts=result.artifacts,
            metadata=result.metadata,
            error=result.error,
            run_id=completed_run.run_id if completed_run else None,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            run_dir=completed_run.artifact_dir if completed_run else None,
        )
        if completed_run is not None:
            self._write_run_files(final, completed_run)
        return final

    def _write_run_files(self, result: ToolResult, run: SandboxRun) -> None:
        if result.stdout:
            (run.artifact_dir / "stdout.txt").write_text(
                result.stdout,
                encoding="utf-8",
            )
        if result.stderr:
            (run.artifact_dir / "stderr.txt").write_text(
                result.stderr,
                encoding="utf-8",
            )
        (run.artifact_dir / "result.json").write_text(
            json.dumps(result.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
