"""Tests for the harness-facing sandbox tool executor."""

import json
from pathlib import Path

import pytest

from agent_sandbox import (
    SandboxToolExecutor,
    SandboxToolPolicy,
    SandboxToolRegistry,
    ToolCall,
    create_fake_sandbox_tools,
)
from agent_sandbox.executor import tool_call_from_mapping


def make_executor(audit_dir: Path | None = None) -> SandboxToolExecutor:
    """Create an executor with fake primitives.

    Args:
        audit_dir: Optional audit directory for tests.

    Returns:
        Executor ready for no-Modal tests.
    """

    tools = create_fake_sandbox_tools(
        SandboxToolPolicy.for_harness(
            allowed_tools=("shell", "python", "screenshot"),
            allowed_shell_commands=("python",),
            allowed_browser_domains=("example.com",),
        )
    )
    return SandboxToolExecutor(SandboxToolRegistry(tools), audit_dir=audit_dir)


def test_executor_lists_registry_tools() -> None:
    """Verify executor discovery delegates to the registry."""

    executor = make_executor()

    assert [tool.name for tool in executor.list_tools()] == [
        "shell",
        "python_code",
        "python_script",
        "screenshot",
    ]


def test_executor_dispatches_tool_call_and_adds_context() -> None:
    """Verify call envelopes dispatch and copy context into result metadata."""

    executor = make_executor()

    result = executor.call(
        ToolCall(
            tool="shell",
            arguments={"command": ["python", "--version"]},
            call_id="call-1",
            agent_id="agent-1",
            task_id="task-1",
            metadata={"purpose": "unit-test"},
        )
    )

    assert result.status == "succeeded"
    assert result.stdout == "fake shell ran: python --version\n"
    assert result.metadata["tool"] == "shell"
    assert result.metadata["call_id"] == "call-1"
    assert result.metadata["agent_id"] == "agent-1"
    assert result.metadata["task_id"] == "task-1"
    assert result.metadata["call_metadata"] == {"purpose": "unit-test"}


def test_executor_call_dict_builds_tool_call() -> None:
    """Verify plain dictionaries can be used as harness call envelopes."""

    executor = make_executor()

    result = executor.call_dict(
        {
            "tool": "python_code",
            "arguments": {"code": "print('hello')"},
            "call_id": "call-2",
        }
    )

    assert result.status == "succeeded"
    assert result.metadata["call_id"] == "call-2"


def test_executor_call_dict_returns_failed_result_for_invalid_envelope() -> None:
    """Verify malformed call dictionaries become structured failed results."""

    executor = make_executor()

    result = executor.call_dict({"arguments": {}})

    assert result.status == "failed"
    assert result.error_code == "invalid_arguments"
    assert result.metadata["tool"] == "<invalid>"


def test_executor_returns_failed_result_for_invalid_payload() -> None:
    """Verify invalid registry arguments become structured failed results."""

    executor = make_executor()

    result = executor.call(ToolCall(tool="shell", arguments={"command": "python"}))

    assert result.status == "failed"
    assert result.error_code == "invalid_arguments"
    assert result.completed_at is not None
    assert result.duration_ms is not None


def test_executor_returns_failed_result_for_policy_denial() -> None:
    """Verify policy denials become structured failed results."""

    tools = create_fake_sandbox_tools(
        SandboxToolPolicy.for_harness(allowed_tools=("python",))
    )
    executor = SandboxToolExecutor(SandboxToolRegistry(tools))

    result = executor.call(
        ToolCall(tool="shell", arguments={"command": ["python", "--version"]})
    )

    assert result.status == "failed"
    assert result.error_code == "policy_denied"
    assert "not allowed" in (result.error or "")


def test_executor_writes_audit_record(tmp_path: Path) -> None:
    """Verify audit logging records the call and result.

    Args:
        tmp_path: Pytest-provided audit directory.
    """

    executor = make_executor(audit_dir=tmp_path)

    result = executor.call(
        ToolCall(
            tool="screenshot",
            arguments={"url": "https://example.com", "output_dir": str(tmp_path)},
            call_id="shot-1",
            agent_id="agent-1",
            metadata={"trace": "abc"},
        )
    )

    assert result.status == "succeeded"
    audit_files = sorted(tmp_path.glob("*shot-1.json"))
    assert len(audit_files) == 1
    payload = json.loads(audit_files[0].read_text(encoding="utf-8"))
    assert payload["call"]["tool"] == "screenshot"
    assert payload["call"]["metadata"] == {"trace": "abc"}
    assert payload["result"]["metadata"]["agent_id"] == "agent-1"
    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["name"] == "screenshot"


def test_executor_writes_audit_record_for_invalid_dict(tmp_path: Path) -> None:
    """Verify malformed call dictionaries can still be audited.

    Args:
        tmp_path: Pytest-provided audit directory.
    """

    executor = make_executor(audit_dir=str(tmp_path))

    result = executor.call_dict({"arguments": []})

    assert result.status == "failed"
    audit_files = sorted(tmp_path.glob("*invalid-tool-call.json"))
    assert len(audit_files) == 1
    payload = json.loads(audit_files[0].read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["error_code"] == "invalid_arguments"


def test_tool_call_from_mapping_rejects_missing_tool() -> None:
    """Verify call envelope validation catches missing tool names."""

    with pytest.raises(ValueError, match="tool"):
        tool_call_from_mapping({"arguments": {}})


def test_tool_call_from_mapping_rejects_non_object_arguments() -> None:
    """Verify call envelope validation catches malformed arguments."""

    with pytest.raises(ValueError, match="arguments"):
        tool_call_from_mapping({"tool": "shell", "arguments": []})


def test_create_fake_sandbox_tools_avoids_modal() -> None:
    """Verify the fake helper can run all core tool types locally."""

    tools = create_fake_sandbox_tools()

    shell = tools.shell(["python", "--version"])
    code = tools.python_code("print('hi')")

    assert shell.status == "succeeded"
    assert code.status == "succeeded"
