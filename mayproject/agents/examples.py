from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mayproject.agents.base import AgentOutcome, AgentSpec
from mayproject.sandbox.results import Artifact

if TYPE_CHECKING:
    from mayproject.workflows.coordinator import AgentContext


@dataclass(frozen=True)
class EchoAgent:
    """Small reference agent for tests and agent authors."""

    spec: AgentSpec = AgentSpec(
        agent_id="echo",
        role="Echo",
        instructions="Return the task objective and inputs.",
    )

    def run(self, context: AgentContext) -> AgentOutcome:
        """Writes a JSON artifact with the task details."""

        payload = {
            "agent_id": self.spec.agent_id,
            "objective": context.task.objective,
            "inputs": context.task.inputs,
        }
        output_path = context.artifact_dir / "echo.json"
        output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        context.emit_event("agent.echo.wrote_artifact", {"path": str(output_path)})
        return AgentOutcome(
            "succeeded",
            output=payload,
            artifacts=(Artifact("echo", "json", output_path, "application/json"),),
        )
