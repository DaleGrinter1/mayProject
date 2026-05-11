# Agent Authoring

Agents are local Python objects that handle one workflow task. They do not need
to know how Modal sandboxes are created or managed. The host project gives each
agent an `AgentContext` with the task, workflow metadata, an artifact directory,
and an event emitter.

## Contract

An agent implements the `Agent` protocol:

```python
from dataclasses import dataclass

from mayproject.agents import AgentOutcome, AgentSpec
from mayproject.workflows import AgentContext


@dataclass(frozen=True)
class MyAgent:
    spec: AgentSpec = AgentSpec(
        agent_id="my-agent",
        role="Researcher",
        instructions="Research the task and return structured findings.",
        allowed_primitives=("browser", "shell"),
    )

    def run(self, context: AgentContext) -> AgentOutcome:
        context.emit_event("agent.note", {"message": "started"})
        return AgentOutcome(
            "succeeded",
            output={"answer": "done"},
        )
```

`agent_id` is the stable plugin key. Keep it lowercase, short, and unique.

## Inputs And Outputs

The workflow gives the agent an `AutomationTask`:

```python
context.task.objective
context.task.inputs
context.task.metadata
```

The agent returns an `AgentOutcome`:

- `status`: usually `"succeeded"` or `"failed"`.
- `output`: JSON-serializable summary data.
- `artifacts`: files written by the agent.
- `sandbox_runs`: sandbox execution records, when the agent uses sandbox tools.
- `error`: plain error detail when the agent fails gracefully.

Agents should write files under `context.artifact_dir` and return those paths as
artifacts.

## Registration

Register agents with `AgentRegistry` and build the coordinator from it:

```python
from mayproject.agents import AgentRegistry
from mayproject.workflows import AutomationTask, WorkflowCoordinator

registry = AgentRegistry([MyAgent()])
workflow = WorkflowCoordinator.from_registry(registry).run(
    AutomationTask("Find the answer"),
)
```

The built-in example agent is available from the command line:

```bash
uv run may-agent list
uv run may-agent run --agent echo "Find the answer"
```

The coordinator runs registered agents in order and writes:

- `workflow.json`
- `events.jsonl`
- per-agent artifacts under `agents/<agent_id>/`

## Sandbox Access

Agents should use `context.capabilities` for sandbox-backed work. Avoid
importing `modal` or primitives directly from agent code. This keeps agents
portable if the sandbox backend changes later.

```python
def run(self, context: AgentContext) -> AgentOutcome:
    result = context.capabilities.shell(["python", "--version"])
    return AgentOutcome(
        "succeeded",
        output={
            "returncode": result.returncode,
            "stdout": result.stdout,
        },
    )
```

Available capabilities:

- `context.capabilities.shell([...])`
- `context.capabilities.python_code("print('hello')")`
- `context.capabilities.python_script(Path("script.py"))`
- `context.capabilities.screenshot("https://example.com")`

Use `allowed_primitives` in `AgentSpec` to describe what the agent expects to
use. The workflow context enforces that list before running a capability.
