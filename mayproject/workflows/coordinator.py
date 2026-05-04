from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mayproject.agents.base import AgentOutcome, AgentSpec
from mayproject.sandbox.results import DEFAULT_RUN_ROOT, Artifact, SandboxRun
from mayproject.workflows.state import (
    AgentRun,
    AutomationTask,
    WorkflowEvent,
    WorkflowRun,
    create_workflow_run,
)


AgentHandler = Callable[["AgentContext"], AgentOutcome]


@dataclass(frozen=True)
class AgentContext:
    task: AutomationTask
    agent: AgentSpec
    workflow: WorkflowRun
    artifact_dir: Path
    emit_event: Callable[[str, dict[str, Any]], WorkflowEvent]


class WorkflowCoordinator:
    def __init__(
        self,
        agents: Iterable[AgentSpec],
        run_root: Path = DEFAULT_RUN_ROOT,
    ) -> None:
        self.agents = tuple(agents)
        self.run_root = run_root

    def run(
        self,
        task: AutomationTask,
        handlers: dict[str, AgentHandler],
    ) -> WorkflowRun:
        workflow = create_workflow_run(task, run_root=self.run_root)
        workflow.write_json()
        self._append_event(workflow, "workflow.started", {"task": task.to_dict()})

        agent_runs: list[AgentRun] = []
        for agent in self.agents:
            agent_run = AgentRun.start(agent)
            agent_runs.append(agent_run)
            self._append_event(
                workflow,
                "agent.started",
                {"agent_run": agent_run.to_dict()},
            )

            handler = handlers.get(agent.agent_id)
            if handler is None:
                completed = agent_run.complete(
                    "failed",
                    error=f"No handler registered for agent: {agent.agent_id}",
                )
            else:
                completed = self._run_agent_handler(task, workflow, agent_run, handler)

            agent_runs[-1] = completed
            self._append_event(
                workflow,
                "agent.completed",
                {"agent_run": completed.to_dict()},
            )

        status = "succeeded" if all(run.status == "succeeded" for run in agent_runs) else "failed"
        workflow = workflow.complete(status, tuple(agent_runs))
        workflow.write_json()
        self._append_event(workflow, "workflow.completed", {"status": status})
        return workflow

    def _run_agent_handler(
        self,
        task: AutomationTask,
        workflow: WorkflowRun,
        agent_run: AgentRun,
        handler: AgentHandler,
    ) -> AgentRun:
        agent = agent_run.agent
        agent_dir = workflow.artifact_dir / "agents" / agent.agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        def emit_event(event_type: str, payload: dict[str, Any]) -> WorkflowEvent:
            return self._append_event(
                workflow,
                event_type,
                {"agent_id": agent.agent_id, **payload},
            )

        context = AgentContext(
            task=task,
            agent=agent,
            workflow=workflow,
            artifact_dir=agent_dir,
            emit_event=emit_event,
        )

        try:
            outcome = handler(context)
        except Exception as exc:
            return agent_run.complete("failed", error=str(exc))

        return agent_run.complete(
            outcome.status,
            output=outcome.output,
            artifacts=outcome.artifacts,
            sandbox_runs=outcome.sandbox_runs,
            error=outcome.error,
        )

    def _append_event(
        self,
        workflow: WorkflowRun,
        event_type: str,
        payload: dict[str, Any],
    ) -> WorkflowEvent:
        event = WorkflowEvent.create(event_type, payload)
        events_path = workflow.artifact_dir / "events.jsonl"
        with events_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")
        return event


def artifact_paths_from_sandbox_runs(runs: Iterable[SandboxRun]) -> tuple[Artifact, ...]:
    artifacts: list[Artifact] = []
    for run in runs:
        artifacts.append(
            Artifact(
                name=f"{run.task_kind}-{run.run_id}",
                kind="sandbox-run",
                path=run.artifact_dir,
            )
        )
    return tuple(artifacts)
