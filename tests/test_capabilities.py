from pathlib import Path
import shutil
from uuid import uuid4

import pytest

from mayproject.sandbox.types import CommandResult
from mayproject.workflows.capabilities import AgentCapabilities


TEST_TMP_ROOT = Path("artifacts") / "test-capabilities"


def workspace_temp_dir() -> Path:
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = TEST_TMP_ROOT / uuid4().hex
    path.mkdir()
    return path


class FakeShellPrimitive:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def run(
        self,
        command: list[str],
        timeout: int | None = None,
        idle_timeout: int | None = None,
    ) -> CommandResult:
        self.commands.append(tuple(command))
        return CommandResult(returncode=0, stdout="shell ok", stderr="")


class FakePythonPrimitive:
    def __init__(self) -> None:
        self.code_runs: list[tuple[str, tuple[str, ...]]] = []
        self.script_runs: list[tuple[Path, tuple[str, ...]]] = []

    def run_code(self, code: str, *args: str) -> CommandResult:
        self.code_runs.append((code, args))
        return CommandResult(returncode=0, stdout="python ok", stderr="")

    def run_script(self, script_path: Path, *args: str) -> CommandResult:
        self.script_runs.append((script_path, args))
        return CommandResult(returncode=0, stdout="script ok", stderr="")


class FakeBrowserPrimitive:
    def __init__(self) -> None:
        self.captures: list[tuple[str, Path, Path]] = []

    def capture_page(self, url: str, image_path: Path, text_path: Path) -> None:
        self.captures.append((url, image_path, text_path))
        image_path.write_bytes(b"fake png")
        text_path.write_text("observation", encoding="utf-8")


def test_shell_capability_runs_allowed_shell_command() -> None:
    shell = FakeShellPrimitive()
    capabilities = AgentCapabilities(
        allowed_primitives=("shell",),
        shell_primitive=shell,
    )

    result = capabilities.shell(["python", "--version"])

    assert result.stdout == "shell ok"
    assert shell.commands == [("python", "--version")]


def test_python_capability_runs_code_and_scripts() -> None:
    python = FakePythonPrimitive()
    capabilities = AgentCapabilities(
        allowed_primitives=("python",),
        python_primitive=python,
    )

    code_result = capabilities.python_code("print('hello')", "arg")
    script_result = capabilities.python_script(Path("script.py"), "arg")

    assert code_result.stdout == "python ok"
    assert script_result.stdout == "script ok"
    assert python.code_runs == [("print('hello')", ("arg",))]
    assert python.script_runs == [(Path("script.py"), ("arg",))]


def test_browser_capability_saves_screenshot_under_agent_artifacts() -> None:
    temp_dir = workspace_temp_dir()
    browser = FakeBrowserPrimitive()
    try:
        capabilities = AgentCapabilities(
            artifact_dir=temp_dir,
            allowed_primitives=("browser",),
            browser_primitive=browser,
        )

        result = capabilities.screenshot("https://example.com")

        assert result.image_path.parent == temp_dir / "screenshots"
        assert result.text_path == result.image_path.with_suffix(".txt")
        assert result.image_path.exists()
        assert result.text_path.read_text(encoding="utf-8") == "observation"
        assert browser.captures[0][0] == "https://example.com"
    finally:
        shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)


def test_capabilities_reject_unlisted_primitives() -> None:
    capabilities = AgentCapabilities(allowed_primitives=("shell",))

    with pytest.raises(PermissionError, match="browser"):
        capabilities.screenshot("https://example.com")
