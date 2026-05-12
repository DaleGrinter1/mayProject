# Tool Registry

`SandboxToolRegistry` is the dynamic adapter for harnesses that want tool
discovery and name-based dispatch instead of direct Python method calls.

```python
from agent_sandbox import SandboxToolPolicy, SandboxToolRegistry, SandboxTools

tools = SandboxTools(
    policy=SandboxToolPolicy(allowed_tools=("shell", "python", "screenshot")),
)
registry = SandboxToolRegistry(tools)

for tool in registry.list_tools():
    print(tool.to_dict())

result = registry.call_tool("shell", {"command": ["python", "--version"]})
```

## Discovery

`list_tools()` returns `ToolSpec` records for tools allowed by policy. Each spec
has:

- `name`
- `description`
- `input_schema`

Schemas are JSON Schema-like dictionaries with `type`, `properties`,
`required`, and `additionalProperties`.

## Tool Names

### `shell`

Runs a command in a temporary sandbox.

```json
{
  "command": ["python", "--version"],
  "timeout": 60,
  "idle_timeout": 20
}
```

Required:

- `command`

### `python_code`

Runs Python source code in a temporary sandbox.

```json
{
  "code": "print('hello')",
  "args": ["optional", "args"]
}
```

Required:

- `code`

### `python_script`

Runs a local Python script in a temporary sandbox.

```json
{
  "script_path": "scripts/check.py",
  "args": ["optional", "args"]
}
```

Required:

- `script_path`

### `screenshot`

Captures a web page screenshot and text observation.

```json
{
  "url": "https://example.com",
  "output_dir": "artifacts/screenshots"
}
```

Required:

- `url`

## Errors

`call_tool()` raises:

- `ValueError` for unknown tool names or invalid argument shapes.
- `PermissionError` when `SandboxToolPolicy` blocks a tool call.

Tool runtime failures return `ToolResult(status="failed")`.

## Policy Names

The registry exposes the screenshot tool as `screenshot`. Policy may grant it
with either `screenshot` or the lower-level `browser` name.
