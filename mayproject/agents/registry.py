from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from mayproject.agents.base import Agent, AgentSpec

if TYPE_CHECKING:
    from mayproject.agents.base import AgentOutcome
    from mayproject.workflows.coordinator import AgentContext

AgentHandler = Callable[["AgentContext"], "AgentOutcome"]


class AgentRegistry:
    """Stores pluggable agents by ID."""

    def __init__(self, agents: Iterable[Agent] = ()) -> None:
        self._agents: dict[str, Agent] = {}
        for agent in agents:
            self.register(agent)

    def register(self, agent: Agent, *, replace: bool = False) -> None:
        """Adds an agent to the registry."""

        agent_id = agent.spec.agent_id
        if agent_id in self._agents and not replace:
            raise ValueError(f"Agent already registered: {agent_id}")
        self._agents[agent_id] = agent

    def get(self, agent_id: str) -> Agent:
        """Returns a registered agent."""

        try:
            return self._agents[agent_id]
        except KeyError as exc:
            raise KeyError(f"Unknown agent: {agent_id}") from exc

    def specs(self) -> tuple[AgentSpec, ...]:
        """Returns the workflow-facing descriptions for all agents."""

        return tuple(agent.spec for agent in self._agents.values())

    def handlers(self) -> dict[str, AgentHandler]:
        """Returns coordinator handlers keyed by agent ID."""

        return {
            agent_id: agent.run
            for agent_id, agent in self._agents.items()
        }
