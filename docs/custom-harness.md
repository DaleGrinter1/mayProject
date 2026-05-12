# Custom Harness Integration

Use `SandboxToolExecutor` when a Python agent harness needs a stable invocation
envelope, policy-aware tool discovery, structured results, and optional audit
records.

## Setup

```python
from pathlib import Path

from agent_sandbox import (
    SandboxToolExecutor,
    SandboxToolPolicy,
    SandboxToolRegistry,
    SandboxTools,
    ToolCall,
)

policy = SandboxToolPolicy.for_harness(
    allowed_tools=("shell", "python", "screenshot"),
    allowed_shell_commands=("python", "pytest"),
    allowed_browser_domains=("example.com",),
    allowed_python_script_roots=("scripts",),
)

tools = SandboxTools(app_name="my-app", policy=policy)
registry = SandboxToolRegistry(tools)
executor = SandboxToolExecutor(
    registry,
    audit_dir=Path(".agent-sandbox/audit"),
)
```

## Discovery

```python
for tool in executor.list_tools():
    print(tool.to_dict())
```

The executor delegates discovery to `SandboxToolRegistry`, so results are
filtered by `SandboxToolPolicy`.

## Invocation

```python
result = executor.call(
    ToolCall(
        tool="shell",
        arguments={"command": ["python", "--version"]},
        call_id="call-123",
        agent_id="agent-a",
        task_id="task-456",
        metadata={"purpose": "environment check"},
    )
)
```

Harness context is copied into `result.metadata` as `call_id`, `agent_id`,
`task_id`, and `call_metadata`.

Plain dictionaries are also accepted:

```python
result = executor.call_dict(
    {
        "tool": "python_code",
        "arguments": {"code": "print('hello')"},
        "call_id": "call-124",
    }
)
```

Malformed dictionaries return `ToolResult(status="failed",
error_code="invalid_arguments")`.

## Audit Records

When `audit_dir` is set, each call writes a JSON record with:

- the original tool call envelope
- the serialized `ToolResult`
- status and `error_code`
- artifact paths
- audit timestamp

Audit records only include metadata the harness explicitly puts in the tool
call. Do not put secrets into call metadata.

## Testing Without Modal

Use the fake helper for harness tests:

```python
from agent_sandbox import SandboxToolExecutor, SandboxToolRegistry
from agent_sandbox import create_fake_sandbox_tools

tools = create_fake_sandbox_tools()
executor = SandboxToolExecutor(SandboxToolRegistry(tools))
```

This exercises orchestration and result handling without creating Modal
resources.

## Example Agent

`examples/example_agent.py` is a deterministic testing agent. It is not an LLM
agent; it maps a few plain-text tasks to executor calls so harness authors can
exercise tool routing, context propagation, audit records, and JSON output.

```bash
uv run python examples/example_agent.py
```

## Real Backend Validation

Run local tests normally:

```bash
uv run pytest
```

Run Modal integration tests only when intentionally validating the real backend:

```bash
AGENT_SANDBOX_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_integration.py
```
