from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from typing import Any, Protocol
from urllib.parse import urlparse

from agent_sandbox.primitives.browser import BrowserPrimitive
from agent_sandbox.primitives.python import PythonPrimitive
from agent_sandbox.primitives.shell import ShellPrimitive
from agent_sandbox.sandbox.results import Artifact
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
    """Declares which sandbox-backed tools a harness may call."""

    allowed_tools: tuple[str, ...] = ()

    def require(self, tool: str) -> None:
        if tool not in self.allowed_tools:
            allowed = ", ".join(self.allowed_tools) or "none"
            raise PermissionError(
                f"Sandbox tool '{tool}' is not allowed. Allowed tools: {allowed}."
            )


@dataclass(frozen=True)
class ToolResult:
    """Structured result returned by harness-facing sandbox tools."""

    status: str
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    artifacts: tuple[Artifact, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

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
        }


@dataclass(frozen=True)
class SandboxTools:
    """Stable tool-provider API for external agent harnesses."""

    app_name: str = "my-app"
    policy: SandboxToolPolicy = SandboxToolPolicy()
    artifact_dir: Path = Path("artifacts/agents")
    shell_primitive: ShellTool | None = None
    python_primitive: PythonTool | None = None
    browser_primitive: BrowserTool | None = None

    def shell(
        self,
        command: Sequence[str],
        timeout: int | None = None,
        idle_timeout: int | None = None,
    ) -> ToolResult:
        """Runs a shell command in a temporary per-task sandbox."""

        self.policy.require("shell")
        primitive = self.shell_primitive or ShellPrimitive(app_name=self.app_name)
        try:
            result = primitive.run(command, timeout=timeout, idle_timeout=idle_timeout)
        except Exception as exc:
            return ToolResult(status="failed", error=str(exc))
        return self._from_command("shell", result, {"command": list(command)})

    def python_code(self, code: str, *args: str) -> ToolResult:
        """Runs Python code in a temporary per-task sandbox."""

        self.policy.require("python")
        primitive = self.python_primitive or PythonPrimitive(app_name=self.app_name)
        try:
            result = primitive.run_code(code, *args)
        except Exception as exc:
            return ToolResult(status="failed", error=str(exc))
        return self._from_command("python", result, {"args": list(args), "source": "code"})

    def python_script(self, script_path: Path, *args: str) -> ToolResult:
        """Runs a local Python script in a temporary per-task sandbox."""

        self.policy.require("python")
        primitive = self.python_primitive or PythonPrimitive(app_name=self.app_name)
        try:
            result = primitive.run_script(script_path, *args)
        except Exception as exc:
            return ToolResult(status="failed", error=str(exc))
        return self._from_command(
            "python",
            result,
            {
                "args": list(args),
                "script_path": str(script_path),
                "source": "script",
            },
        )

    def screenshot(
        self,
        url: str,
        output_dir: Path | None = None,
    ) -> ToolResult:
        """Captures a web page in a temporary browser sandbox."""

        self.policy.require("browser")
        target_dir = output_dir or self.artifact_dir / "screenshots"
        image_path = tool_screenshot_path(url, target_dir)
        text_path = image_path.with_suffix(".txt")
        primitive = self.browser_primitive or BrowserPrimitive(app_name=self.app_name)
        try:
            primitive.capture_page(url, image_path, text_path)
        except Exception as exc:
            return ToolResult(
                status="failed",
                metadata={
                    "tool": "browser",
                    "url": url,
                    "image_path": str(image_path),
                    "text_path": str(text_path),
                },
                error=str(exc),
            )

        artifacts = (
            Artifact("screenshot", "image", image_path, "image/png"),
            Artifact("observation", "text", text_path, "text/plain"),
        )
        return ToolResult(
            status="succeeded",
            returncode=0,
            artifacts=artifacts,
            metadata={
                "tool": "browser",
                "url": url,
                "image_path": str(image_path),
                "text_path": str(text_path),
            },
        )

    def _from_command(
        self,
        tool: str,
        result: CommandResult,
        metadata: dict[str, Any],
    ) -> ToolResult:
        return ToolResult(
            status="succeeded" if result.returncode == 0 else "failed",
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            metadata={"tool": tool, **metadata},
        )
