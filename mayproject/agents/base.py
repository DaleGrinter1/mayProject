from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from mayproject.sandbox.results import Artifact, SandboxRun

if TYPE_CHECKING:
    from mayproject.workflows.coordinator import AgentContext


@dataclass(frozen=True)
class AgentSpec:
    """Describes an agent that can participate in a workflow."""

    agent_id: str
    role: str
    instructions: str = ""
    allowed_primitives: tuple[str, ...] = ()
    sandbox_limit: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "instructions": self.instructions,
            "allowed_primitives": list(self.allowed_primitives),
            "sandbox_limit": self.sandbox_limit,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class AgentOutcome:
    """Describes what an agent produced while handling a task."""

    status: str
    output: dict[str, Any] = field(default_factory=dict)
    artifacts: tuple[Artifact, ...] = ()
    sandbox_runs: tuple[SandboxRun, ...] = ()
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "output": dict(self.output),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "sandbox_runs": [run.to_dict() for run in self.sandbox_runs],
            "error": self.error,
        }


class Agent(Protocol):
    """Contract implemented by pluggable workflow agents."""

    spec: AgentSpec

    def run(self, context: AgentContext) -> AgentOutcome:
        """Runs this agent for one workflow task."""
        ...
