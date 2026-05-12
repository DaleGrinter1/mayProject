"""Tests for the deterministic example agent."""

import json
from pathlib import Path

from examples.example_agent import ExampleAgent, create_example_agent, main


def test_example_agent_routes_python_version_to_shell() -> None:
    """Verify the example agent can exercise shell tool calls."""

    agent = create_example_agent()

    run = agent.run("check python")

    assert run.call.tool == "shell"
    assert run.call.arguments == {"command": ["python", "--version"]}
    assert run.result.status == "succeeded"
    assert run.result.metadata["agent_id"] == "example-agent"


def test_example_agent_routes_python_prefix_to_python_code() -> None:
    """Verify the example agent can exercise Python code tool calls."""

    agent = create_example_agent()

    run = agent.run("python: print('hi')")

    assert run.call.tool == "python_code"
    assert run.call.arguments == {"code": "print('hi')"}
    assert run.result.status == "succeeded"


def test_example_agent_routes_screenshot_task(tmp_path: Path) -> None:
    """Verify the example agent can exercise screenshot tool calls.

    Args:
        tmp_path: Pytest-provided audit directory.
    """

    agent = create_example_agent(audit_dir=tmp_path)

    run = agent.run("screenshot https://example.com")

    assert run.call.tool == "screenshot"
    assert run.call.arguments == {"url": "https://example.com"}
    assert run.result.status == "succeeded"
    assert sorted(tmp_path.glob("*.json"))


def test_example_agent_falls_back_to_python_echo() -> None:
    """Verify unknown tasks still produce a safe deterministic tool call."""

    agent = create_example_agent()

    run = agent.run("summarize this")

    assert run.call.tool == "python_code"
    assert run.call.arguments == {"code": "print('summarize this')"}
    assert run.result.status == "succeeded"


def test_example_agent_run_serializes() -> None:
    """Verify example agent runs can be serialized as JSON."""

    agent = create_example_agent()

    payload = agent.run("check python").to_dict()

    assert json.loads(json.dumps(payload))["result"]["status"] == "succeeded"


def test_example_agent_main_prints_json(capsys) -> None:
    """Verify the example script runs as a smoke test."""

    result = main()

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert [item["call"]["tool"] for item in payload] == [
        "shell",
        "python_code",
        "screenshot",
    ]
