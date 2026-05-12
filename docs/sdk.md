# SDK

`SandboxTools` is the public Python API for agent harnesses. The harness owns
planning and orchestration; `agent-sandbox` owns isolated execution.

```python
from agent_sandbox import SandboxToolPolicy, SandboxTools

tools = SandboxTools(
    policy=SandboxToolPolicy(allowed_tools=("shell", "python", "browser")),
)

result = tools.shell(["python", "--version"])
```

## Result Contract

Every SDK method returns `ToolResult` unless the call is blocked by policy.

Stable fields:

- `status`: `succeeded` or `failed`.
- `returncode`: process return code when applicable.
- `stdout`: captured standard output.
- `stderr`: captured standard error.
- `artifacts`: files produced by the tool.
- `metadata`: JSON-friendly tool details.
- `error`: setup or execution error text.
- `run_id`, `run_dir`: populated when run recording is enabled.
- `started_at`, `completed_at`, `duration_ms`: timing metadata.

Policy violations raise `PermissionError`. Sandbox startup, command, copy, and
browser failures return `ToolResult(status="failed")`.

## Run Recording

Run recording is optional:

```python
tools = SandboxTools(
    policy=SandboxToolPolicy(allowed_tools=("shell",)),
    record_runs=True,
)
```

Recorded calls write under `.agent-sandbox/runs/`:

```text
result.json
stdout.txt
stderr.txt
artifacts/
```

Use this while developing or debugging a harness. Leave it off for lightweight
production calls unless you need local audit files.
