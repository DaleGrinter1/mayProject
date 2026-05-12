"""Testing pattern for harnesses that use agent-sandbox.

Harness authors can inject primitive objects into `SandboxTools` to test their
own orchestration code without launching Modal sandboxes.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_sandbox import SandboxToolPolicy, SandboxTools
from agent_sandbox.sandbox.types import CommandResult


class FakeShellPrimitive:
    """Small shell fake that returns predictable output."""

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
    """Small Python fake that avoids remote execution."""

    def run_code(self, code: str, *args: str) -> CommandResult:
        return CommandResult(
            returncode=0,
            stdout=json.dumps({"source": "code", "args": list(args), "code": code}),
            stderr="",
        )

    def run_script(self, script_path: Path, *args: str) -> CommandResult:
        return CommandResult(
            returncode=0,
            stdout=json.dumps(
                {
                    "source": "script",
                    "script_path": str(script_path),
                    "args": list(args),
                }
            ),
            stderr="",
        )


class FakeBrowserPrimitive:
    """Small browser fake that writes local artifact placeholders."""

    def capture_page(self, url: str, image_path: Path, text_path: Path) -> None:
        image_path.write_bytes(b"fake-png")
        text_path.write_text(f"fake observation for {url}\n", encoding="utf-8")


def main() -> int:
    """Run fake tool calls and print their structured result dictionaries."""

    tools = SandboxTools(
        policy=SandboxToolPolicy(
            allowed_tools=("shell", "python", "screenshot"),
            allowed_shell_commands=("python",),
            allowed_browser_domains=("example.com",),
        ),
        shell_primitive=FakeShellPrimitive(),
        python_primitive=FakePythonPrimitive(),
        browser_primitive=FakeBrowserPrimitive(),
    )

    results = [
        tools.shell(["python", "--version"]),
        tools.python_code("print('hello')"),
        tools.screenshot("https://example.com"),
    ]
    print(json.dumps([result.to_dict() for result in results], indent=2))
    return int(any(result.status != "succeeded" for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
