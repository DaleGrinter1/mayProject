from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from mayproject.agents.base import AgentSpec
from mayproject.sandbox.results import (
    DEFAULT_RUN_ROOT,
    Artifact,
    SandboxRun,
    format_timestamp,
    safe_slug,
    utc_now,
)


@dataclass(frozen=True)
class AutomationTask:
    objective: str
    task_id: str = field(default_factory=lambda: uuid4().hex[:8])
    inputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "objective": self.objective,
            "inputs": dict(self.inputs),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class WorkflowEvent:
    event_type: str
    payload: dict[str, Any]
    created_at: datetime = field(default_factory=utc_now)
    event_id: str = field(default_factory=lambda: uuid4().hex[:8])

    @classmethod
    def create(cls, event_type: str, payload: dict[str, Any]) -> "WorkflowEvent":
        return cls(event_type=event_type, payload=dict(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "created_at": self.created_at.isoformat(),
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class AgentRun:
    agent: AgentSpec
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    output: dict[str, Any] = field(default_factory=dict)
    artifacts: tuple[Artifact, ...] = ()
    sandbox_runs: tuple[SandboxRun, ...] = ()
    error: str | None = None

    @classmethod
    def start(cls, agent: AgentSpec) -> "AgentRun":
        return cls(agent=agent, status="running", started_at=utc_now())

    def complete(
        self,
        status: str,
        output: dict[str, Any] | None = None,
        artifacts: tuple[Artifact, ...] = (),
        sandbox_runs: tuple[SandboxRun, ...] = (),
        error: str | None = None,
    ) -> "AgentRun":
        return replace(
            self,
            status=status,
            completed_at=utc_now(),
            output=dict(output or {}),
            artifacts=artifacts,
            sandbox_runs=sandbox_runs,
            error=error,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent.to_dict(),
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "output": dict(self.output),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "sandbox_runs": [run.to_dict() for run in self.sandbox_runs],
            "error": self.error,
        }


@dataclass(frozen=True)
class WorkflowRun:
    task: AutomationTask
    workflow_id: str
    artifact_dir: Path
    started_at: datetime
    status: str = "running"
    completed_at: datetime | None = None
    agent_runs: tuple[AgentRun, ...] = ()

    def complete(self, status: str, agent_runs: tuple[AgentRun, ...]) -> "WorkflowRun":
        return replace(
            self,
            status=status,
            completed_at=utc_now(),
            agent_runs=agent_runs,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "task": self.task.to_dict(),
            "artifact_dir": str(self.artifact_dir),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "agent_runs": [run.to_dict() for run in self.agent_runs],
        }

    def write_json(self) -> None:
        path = self.artifact_dir / "workflow.json"
        path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )


def create_workflow_run(
    task: AutomationTask,
    run_root: Path = DEFAULT_RUN_ROOT,
    started_at: datetime | None = None,
    workflow_id: str | None = None,
) -> WorkflowRun:
    started_at = started_at or utc_now()
    workflow_id = workflow_id or uuid4().hex[:8]
    directory_name = (
        f"{format_timestamp(started_at)}-workflow-"
        f"{safe_slug(task.objective)[:32]}-{safe_slug(workflow_id)[:8]}"
    )
    artifact_dir = run_root / directory_name
    artifact_dir.mkdir(parents=True, exist_ok=False)
    return WorkflowRun(
        task=task,
        workflow_id=workflow_id,
        artifact_dir=artifact_dir,
        started_at=started_at,
    )
