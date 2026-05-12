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

Harnesses that need dynamic discovery and name-based dispatch can wrap the SDK
with `SandboxToolRegistry`:

```python
from agent_sandbox import SandboxToolRegistry

registry = SandboxToolRegistry(tools)
available_tools = registry.list_tools()
result = registry.call_tool("shell", {"command": ["python", "--version"]})
```

See `docs/registry.md` for registry tool names and argument schemas.
See `docs/custom-harness.md` for the higher-level executor with call envelopes
and audit logging.

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
- `error_code`: machine-readable error category for failed results.
- `run_id`, `run_dir`: populated when run recording is enabled.
- `started_at`, `completed_at`, `duration_ms`: timing metadata.

Policy violations raise `PermissionError`. Sandbox startup, command, copy, and
browser failures return `ToolResult(status="failed")`.

## Tool Policy

`SandboxToolPolicy` is an allowlist. A harness must opt in to each tool it plans
to call:

```python
tools = SandboxTools(
    policy=SandboxToolPolicy(allowed_tools=("shell", "python")),
)
```

Calling a tool that is not allowed raises `PermissionError` before a sandbox is
started.

Policies can also narrow shell, browser, and timeout behavior:

```python
tools = SandboxTools(
    policy=SandboxToolPolicy(
        allowed_tools=("shell", "screenshot"),
        allowed_shell_commands=("python", "pytest"),
        allowed_browser_domains=("example.com",),
        allowed_python_script_roots=("scripts",),
        max_timeout=60,
        max_idle_timeout=20,
    ),
)
```

`allowed_shell_commands` checks the executable name, such as `python` in
`["python", "--version"]`. `allowed_browser_domains` accepts exact hosts and
subdomains. `allowed_python_script_roots` restricts local script files that
`python_script` may copy into a sandbox.

`browser` remains the low-level policy name for browser-backed tools.
`screenshot` is accepted as a clearer alias for screenshot-only harnesses.

## Artifacts

Screenshot calls produce two artifacts:

- `screenshot`: a PNG image.
- `observation`: a text file captured alongside the screenshot.

When run recording is disabled, screenshot artifacts default to
`artifacts/agents/screenshots/` unless an output directory is passed.

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

## Scope

The SDK is a tool-provider layer, not a full agent runtime. It does not manage
planning, memory, user sessions, model calls, or multi-step orchestration.

## Example Harness

`examples/harness_runner.py` shows a small external-harness shape: parse a tool
request, grant only that tool through `SandboxToolPolicy`, call the dynamic
registry, and print `ToolResult` as JSON.

```bash
uv run python examples/harness_runner.py shell -- python --version
uv run python examples/harness_runner.py python-code "print('hello from sandbox')"
uv run python examples/harness_runner.py screenshot https://example.com
```
