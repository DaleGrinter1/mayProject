from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from mayproject.primitives.browser import BrowserPrimitive
from mayproject.primitives.python import PythonPrimitive
from mayproject.primitives.shell import ShellPrimitive
from mayproject.sandbox.types import CommandResult
from mayproject.workflows.screenshot import ScreenshotResult, screenshot_path


class ShellCapability(Protocol):
    def run(
        self,
        command: Sequence[str],
        timeout: int | None = None,
        idle_timeout: int | None = None,
    ) -> CommandResult: ...


class PythonCapability(Protocol):
    def run_code(self, code: str, *args: str) -> CommandResult: ...

    def run_script(self, script_path: Path, *args: str) -> CommandResult: ...


class BrowserCapability(Protocol):
    def capture_page(self, url: str, image_path: Path, text_path: Path) -> None: ...


@dataclass(frozen=True)
class AgentCapabilities:
    """Provides sandbox-backed tools to one agent."""

    app_name: str = "my-app"
    artifact_dir: Path = Path("artifacts/agents")
    allowed_primitives: tuple[str, ...] = ()
    shell_primitive: ShellCapability | None = None
    python_primitive: PythonCapability | None = None
    browser_primitive: BrowserCapability | None = None

    def shell(
        self,
        command: Sequence[str],
        timeout: int | None = None,
        idle_timeout: int | None = None,
    ) -> CommandResult:
        """Runs a shell command in a temporary sandbox."""

        self._require("shell")
        primitive = self.shell_primitive or ShellPrimitive(app_name=self.app_name)
        return primitive.run(command, timeout=timeout, idle_timeout=idle_timeout)

    def python_code(self, code: str, *args: str) -> CommandResult:
        """Runs Python code in a temporary sandbox."""

        self._require("python")
        primitive = self.python_primitive or PythonPrimitive(app_name=self.app_name)
        return primitive.run_code(code, *args)

    def python_script(self, script_path: Path, *args: str) -> CommandResult:
        """Runs a local Python script in a temporary sandbox."""

        self._require("python")
        primitive = self.python_primitive or PythonPrimitive(app_name=self.app_name)
        return primitive.run_script(script_path, *args)

    def screenshot(
        self,
        url: str,
        output_dir: Path | None = None,
    ) -> ScreenshotResult:
        """Captures a web page in a temporary browser sandbox."""

        self._require("browser")
        target_dir = output_dir or self.artifact_dir / "screenshots"
        image_path = screenshot_path(url, target_dir)
        text_path = image_path.with_suffix(".txt")
        primitive = self.browser_primitive or BrowserPrimitive(app_name=self.app_name)
        primitive.capture_page(url, image_path, text_path)
        return ScreenshotResult(url=url, image_path=image_path, text_path=text_path)

    def _require(self, primitive: str) -> None:
        if primitive not in self.allowed_primitives:
            allowed = ", ".join(self.allowed_primitives) or "none"
            raise PermissionError(
                f"Agent is not allowed to use primitive '{primitive}'. "
                f"Allowed primitives: {allowed}."
            )
