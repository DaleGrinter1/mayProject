"""Deterministic example agent for testing harness integrations.

This is not an LLM agent. It is a tiny rule-based agent that exercises the
same executor path a real harness would use, which makes it useful for tests,
demos, and smoke checks without model credentials or Modal resources.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from agent_sandbox import (
    SandboxToolExecutor,
    SandboxToolRegistry,
    ToolCall,
    ToolResult,
    create_fake_sandbox_tools,
)


@dataclass(frozen=True)
class ExampleAgentRun:
    """Result of one example-agent task."""

    task: str
    call: ToolCall
    result: ToolResult

    def to_dict(self) -> dict[str, object]:
        """Serialize the agent run for demos and tests."""

        return {
            "task": self.task,
            "call": self.call.to_dict(),
            "result": self.result.to_dict(),
        }


@dataclass(frozen=True)
class ExampleAgent:
    """Small deterministic agent that routes tasks to sandbox tools."""

    executor: SandboxToolExecutor
    agent_id: str = "example-agent"

    def run(self, task: str) -> ExampleAgentRun:
        """Choose one tool call for a task and execute it.

        Args:
            task: Plain-text task such as `check python`, `python: print(1)`,
                or `screenshot https://example.com`.

        Returns:
            Agent run with the selected call and structured tool result.
        """

        call = self._plan(task)
        return ExampleAgentRun(
            task=task,
            call=call,
            result=self.executor.call(call),
        )

    def _plan(self, task: str) -> ToolCall:
        normalized = task.strip()
        lowered = normalized.lower()

        if lowered in {"check python", "python version"}:
            return self._call(
                "shell",
                {"command": ["python", "--version"]},
                task=normalized,
            )

        if lowered.startswith("python:"):
            return self._call(
                "python_code",
                {"code": normalized.split(":", 1)[1].strip()},
                task=normalized,
            )

        if lowered.startswith("screenshot "):
            url = normalized.split(maxsplit=1)[1]
            return self._call(
                "screenshot",
                {"url": url},
                task=normalized,
            )

        return self._call(
            "python_code",
            {"code": f"print({normalized!r})"},
            task=normalized,
        )

    def _call(self, tool: str, arguments: dict[str, object], task: str) -> ToolCall:
        return ToolCall(
            tool=tool,
            arguments=arguments,
            agent_id=self.agent_id,
            metadata={"task": task},
        )


def create_example_agent(audit_dir: Path | str | None = None) -> ExampleAgent:
    """Create an example agent backed by fake sandbox tools.

    Args:
        audit_dir: Optional audit directory for executor call records.

    Returns:
        Example agent that does not launch Modal resources.
    """

    executor = SandboxToolExecutor(
        SandboxToolRegistry(create_fake_sandbox_tools()),
        audit_dir=audit_dir,
    )
    return ExampleAgent(executor)


def main() -> int:
    """Run a small smoke-test sequence and print JSON."""

    agent = create_example_agent()
    tasks = [
        "check python",
        "python: print('hello from the example agent')",
        "screenshot https://example.com",
    ]
    runs = [agent.run(task).to_dict() for task in tasks]
    print(json.dumps(runs, indent=2, sort_keys=True))
    return int(any(run["result"]["status"] != "succeeded" for run in runs))


if __name__ == "__main__":
    raise SystemExit(main())
