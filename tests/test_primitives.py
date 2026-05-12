from pathlib import Path

import pytest

from agent_sandbox.primitives.browser import BrowserPrimitive
from agent_sandbox.primitives.python import PythonPrimitive
from agent_sandbox.primitives.shell import ShellPrimitive
from agent_sandbox.sandbox.fake import FakeSandboxRunner
from agent_sandbox.sandbox.types import CommandResult, SandboxSpec


class RunnerRecorder:
    def __init__(self) -> None:
        self.runners: list[FakeSandboxRunner] = []

    def factory(self, spec: SandboxSpec) -> FakeSandboxRunner:
        runner = FakeSandboxRunner(spec)
        self.runners.append(runner)
        return runner


def test_shell_primitive_rejects_empty_command() -> None:
    with pytest.raises(ValueError, match="at least one argument"):
        ShellPrimitive().run([])


def test_shell_primitive_executes_command_with_fake_runner() -> None:
    recorder = RunnerRecorder()

    result = ShellPrimitive(runner_factory=recorder.factory).run(["echo", "hello"])

    assert result.returncode == 0
    assert recorder.runners[0].commands == [("echo", "hello")]
    assert recorder.runners[0].spec.tags == {"primitive": "shell"}


def test_python_primitive_writes_code_and_executes_it() -> None:
    recorder = RunnerRecorder()

    PythonPrimitive(runner_factory=recorder.factory).run_code("print('hi')", "x")

    runner = recorder.runners[0]
    assert runner.writes == [("print('hi')", "/tmp/script.py")]
    assert runner.commands == [("python", "/tmp/script.py", "x")]


def test_browser_primitive_copies_script_and_outputs() -> None:
    recorder = RunnerRecorder()

    BrowserPrimitive(runner_factory=recorder.factory).capture_page(
        "https://example.com",
        Path("out.png"),
        Path("out.txt"),
    )

    runner = recorder.runners[0]
    assert runner.copied_from_local[0][0].name == "screenshot_page.py"
    assert runner.copied_from_local[0][1] == "/tmp/screenshot.py"
    assert runner.commands == [
        (
            "python",
            "/tmp/screenshot.py",
            "https://example.com",
            "/tmp/screenshot.png",
            "/tmp/observation.txt",
        )
    ]
    assert runner.copied_to_local == [
        ("/tmp/screenshot.png", Path("out.png")),
        ("/tmp/observation.txt", Path("out.txt")),
    ]


def test_browser_primitive_raises_on_failed_capture() -> None:
    def factory(spec: SandboxSpec) -> FakeSandboxRunner:
        return FakeSandboxRunner(
            spec,
            command_handler=lambda command: CommandResult(
                returncode=1,
                stdout="",
                stderr="boom",
            ),
        )

    with pytest.raises(RuntimeError, match="boom"):
        BrowserPrimitive(runner_factory=factory).capture_page(
            "https://example.com",
            Path("out.png"),
            Path("out.txt"),
        )

