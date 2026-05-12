"""Tests for the dynamic sandbox tool registry."""

from pathlib import Path

import pytest

from agent_sandbox import SandboxToolPolicy, SandboxToolRegistry, SandboxTools
from agent_sandbox.sandbox.types import CommandResult


class FakeShellPrimitive:
    """Shell fake for registry dispatch tests."""

    def run(
        self,
        command: list[str],
        timeout: int | None = None,
        idle_timeout: int | None = None,
    ) -> CommandResult:
        return CommandResult(
            returncode=0,
            stdout=f"{command}:{timeout}:{idle_timeout}",
            stderr="",
        )


class FakePythonPrimitive:
    """Python fake for registry dispatch tests."""

    def run_code(self, code: str, *args: str) -> CommandResult:
        return CommandResult(returncode=0, stdout=f"code:{code}:{args}", stderr="")

    def run_script(self, script_path: Path, *args: str) -> CommandResult:
        return CommandResult(
            returncode=0,
            stdout=f"script:{script_path}:{args}",
            stderr="",
        )


class FakeBrowserPrimitive:
    """Browser fake for registry dispatch tests."""

    def capture_page(self, url: str, image_path: Path, text_path: Path) -> None:
        image_path.write_bytes(b"png")
        text_path.write_text(url, encoding="utf-8")


def make_registry(policy: SandboxToolPolicy) -> SandboxToolRegistry:
    """Create a registry with all primitives faked.

    Args:
        policy: Policy to attach to the SDK tools.

    Returns:
        Registry ready for dynamic dispatch tests.
    """

    return SandboxToolRegistry(
        SandboxTools(
            policy=policy,
            shell_primitive=FakeShellPrimitive(),
            python_primitive=FakePythonPrimitive(),
            browser_primitive=FakeBrowserPrimitive(),
        )
    )


def test_registry_lists_policy_allowed_tools() -> None:
    """Verify discovery only includes tools allowed by policy."""

    registry = make_registry(SandboxToolPolicy(allowed_tools=("python", "browser")))

    assert [tool.name for tool in registry.list_tools()] == [
        "python_code",
        "python_script",
        "screenshot",
    ]
    assert registry.list_tools()[0].to_dict()["input_schema"]["type"] == "object"


def test_registry_lists_screenshot_policy_alias() -> None:
    """Verify screenshot policy grants the screenshot registry tool."""

    registry = make_registry(SandboxToolPolicy(allowed_tools=("screenshot",)))

    assert [tool.name for tool in registry.list_tools()] == ["screenshot"]


def test_registry_specs_have_strict_object_schemas() -> None:
    """Verify every registry spec advertises a strict object argument schema."""

    registry = make_registry(
        SandboxToolPolicy(allowed_tools=("shell", "python", "browser"))
    )

    for spec in registry.list_tools():
        schema = spec.input_schema
        assert schema["type"] == "object"
        assert isinstance(schema["properties"], dict)
        assert isinstance(schema["required"], list)
        assert schema["additionalProperties"] is False


def test_registry_calls_shell_tool_by_name() -> None:
    """Verify registry dispatch forwards shell arguments."""

    registry = make_registry(SandboxToolPolicy(allowed_tools=("shell",)))

    result = registry.call_tool(
        "shell",
        {
            "command": ["python", "--version"],
            "timeout": 30,
            "idle_timeout": 5,
        },
    )

    assert result.status == "succeeded"
    assert result.stdout == "['python', '--version']:30:5"


def test_registry_calls_python_code_by_name() -> None:
    """Verify registry dispatch forwards Python code arguments."""

    registry = make_registry(SandboxToolPolicy(allowed_tools=("python",)))

    result = registry.call_tool("python_code", {"code": "print(1)", "args": ["x"]})

    assert result.status == "succeeded"
    assert result.stdout == "code:print(1):('x',)"


def test_registry_calls_python_script_by_name() -> None:
    """Verify registry dispatch converts script paths."""

    registry = make_registry(SandboxToolPolicy(allowed_tools=("python",)))

    result = registry.call_tool(
        "python_script",
        {"script_path": "script.py", "args": ["x"]},
    )

    assert result.status == "succeeded"
    assert result.stdout == "script:script.py:('x',)"


def test_registry_calls_screenshot_by_name(tmp_path: Path) -> None:
    """Verify registry dispatch forwards screenshot arguments.

    Args:
        tmp_path: Pytest-provided temporary output directory.
    """

    registry = make_registry(
        SandboxToolPolicy(
            allowed_tools=("browser",),
            allowed_browser_domains=("example.com",),
        )
    )

    result = registry.call_tool(
        "screenshot",
        {"url": "https://example.com", "output_dir": str(tmp_path)},
    )

    assert result.status == "succeeded"
    assert result.image_path is not None
    assert result.image_path.exists()
    assert result.text_path is not None
    assert result.text_path.read_text(encoding="utf-8") == "https://example.com"


def test_registry_rejects_unknown_tool() -> None:
    """Verify unknown registry names fail clearly."""

    registry = make_registry(SandboxToolPolicy(allowed_tools=("shell",)))

    with pytest.raises(ValueError, match="Unknown sandbox tool"):
        registry.call_tool("missing", {})


def test_registry_rejects_invalid_arguments() -> None:
    """Verify invalid argument shapes fail before SDK dispatch."""

    registry = make_registry(SandboxToolPolicy(allowed_tools=("shell",)))

    with pytest.raises(ValueError, match="list of strings"):
        registry.call_tool("shell", {"command": "python --version"})


def test_registry_rejects_unknown_arguments() -> None:
    """Verify registry calls match the advertised schemas."""

    registry = make_registry(SandboxToolPolicy(allowed_tools=("shell",)))

    with pytest.raises(ValueError, match="Unknown tool argument"):
        registry.call_tool("shell", {"command": ["python"], "extra": True})


def test_registry_still_honors_sdk_policy() -> None:
    """Verify dynamic calls cannot bypass SDK policy."""

    registry = make_registry(SandboxToolPolicy(allowed_tools=("python",)))

    with pytest.raises(PermissionError, match="shell"):
        registry.call_tool("shell", {"command": ["python", "--version"]})
