# Harness Integration

`agent-sandbox` is the execution layer for an agent harness. The harness owns
agents, model calls, planning, memory, user sessions, and approval decisions.
This package owns sandbox-backed tools and structured execution results.

## Integration Shape

```text
agent harness
  -> decides which tool call is allowed
  -> calls SandboxToolExecutor, SandboxToolRegistry, or SandboxTools
  -> receives ToolResult
  -> decides the agent's next step
```

Use the SDK from `agent_sandbox`:

```python
from agent_sandbox import SandboxToolPolicy, SandboxTools

tools = SandboxTools(
    app_name="my-app",
    policy=SandboxToolPolicy(allowed_tools=("shell", "python", "browser")),
)
```

If the harness has a dynamic tool loop, use `SandboxToolRegistry`:

```python
from agent_sandbox import SandboxToolRegistry

registry = SandboxToolRegistry(tools)
for tool in registry.list_tools():
    print(tool.to_dict())

result = registry.call_tool("shell", {"command": ["python", "--version"]})
```

For a full harness invocation envelope and optional audit records, use
`SandboxToolExecutor`. See `docs/custom-harness.md`.

## Policy

Start with the narrowest useful tool list:

```python
policy = SandboxToolPolicy(allowed_tools=("python",))
```

For shell and browser access, add guardrails when the harness can know them in
advance:

```python
policy = SandboxToolPolicy(
    allowed_tools=("shell", "screenshot"),
    allowed_shell_commands=("python", "pytest"),
    allowed_browser_domains=("example.com", "docs.example.com"),
    allowed_python_script_roots=("scripts",),
    max_timeout=60,
    max_idle_timeout=20,
)
```

Policy failures raise `PermissionError` before a sandbox is started. Runtime
failures return `ToolResult(status="failed")` with `error_code` when a stable
category is available.

## Result Handling

Every SDK call returns `ToolResult` with stable fields:

- `status`
- `returncode`
- `stdout`
- `stderr`
- `artifacts`
- `metadata`
- `error`
- `error_code`
- timing fields
- optional run-recording fields

Harnesses should branch on `status` and keep `metadata` with any agent trace.
Use `to_dict()` when serializing results into logs or eval records.

## Dynamic Tool Registry

`SandboxToolRegistry` exposes a small adapter for harnesses that want tool
discovery and name-based calls:

- `list_tools()` returns policy-aware `ToolSpec` records.
- `call_tool(name, arguments)` dispatches to the matching SDK method.
- Unknown tool names and invalid argument shapes raise `ValueError`.
- Policy violations still raise `PermissionError`.

Registry tool names:

- `shell`
- `python_code`
- `python_script`
- `screenshot`

See `docs/registry.md` for argument shapes and schema details.

## Temporary Calls vs Managed Sandboxes

Use `SandboxTools` for normal agent tool calls. SDK calls create temporary
per-task sandboxes by default.

Use managed sandbox commands for debugging, manual inspection, repeated remote
work, attached volumes, or interactive shells:

```bash
uv run agent-sandbox create --name devbox --image dev
uv run agent-sandbox exec --name devbox -- python --version
uv run agent-sandbox terminate --name devbox
```

## Testing A Harness

Harness tests should inject fake primitives so they can validate orchestration
without launching Modal resources. See `examples/fake_primitives.py` for the
pattern.

Run real Modal integration tests separately and intentionally:

```bash
AGENT_SANDBOX_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_integration.py
```

## Example

`examples/harness_runner.py` is a compact harness-style entry point. It parses a
tool request, grants only that tool through policy, calls the registry, and
prints structured JSON.

```bash
uv run python examples/harness_runner.py shell -- python --version
uv run python examples/harness_runner.py python-code "print('hello')"
uv run python examples/harness_runner.py screenshot https://example.com
```
