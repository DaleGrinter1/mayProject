from __future__ import annotations

from pathlib import Path

from agent_sandbox.sandbox.types import CommandResult
from agent_sandbox.tools import SandboxToolPolicy, SandboxTools


class FakeShellPrimitive:
    """Fake shell primitive for harness tests that should not launch Modal."""

    def run(
        self,
        command: list[str],
        timeout: int | None = None,
        idle_timeout: int | None = None,
    ) -> CommandResult:
        return CommandResult(
            returncode=0,
            stdout=f"fake shell ran: {' '.join(command)}\n",
            stderr="",
        )


class FakePythonPrimitive:
    """Fake Python primitive for harness tests that should not launch Modal."""

    def run_code(self, code: str, *args: str) -> CommandResult:
        return CommandResult(
            returncode=0,
            stdout=f"fake python code ran with {len(args)} args\n",
            stderr="",
        )

    def run_script(self, script_path: Path, *args: str) -> CommandResult:
        return CommandResult(
            returncode=0,
            stdout=f"fake python script ran: {script_path}\n",
            stderr="",
        )


class FakeBrowserPrimitive:
    """Fake browser primitive that writes local placeholder artifacts."""

    def capture_page(self, url: str, image_path: Path, text_path: Path) -> None:
        image_path.write_bytes(b"fake-png")
        text_path.write_text(f"fake observation for {url}\n", encoding="utf-8")


def create_fake_sandbox_tools(
    policy: SandboxToolPolicy | None = None,
) -> SandboxTools:
    """Create `SandboxTools` wired to fake primitives for harness tests.

    Args:
        policy: Optional policy. Defaults to all registry tools enabled.

    Returns:
        SandboxTools instance that avoids Modal-backed execution.
    """

    return SandboxTools(
        policy=policy
        or SandboxToolPolicy.for_harness(
            allowed_tools=("shell", "python", "screenshot"),
        ),
        shell_primitive=FakeShellPrimitive(),
        python_primitive=FakePythonPrimitive(),
        browser_primitive=FakeBrowserPrimitive(),
    )
