# Protocol Adapters

`SandboxToolExecutor` and `SandboxToolRegistry` are the boundaries to use when
exposing these tools through another protocol.

The executor and registry provide the pieces most adapters need:

- `list_tools()` for discovery.
- `ToolSpec.input_schema` for argument schemas.
- `SandboxToolExecutor.call(...)` for envelope-based dispatch and audit.
- `SandboxToolRegistry.call_tool(name, arguments)` for lower-level dispatch.
- `ToolResult.to_dict()` for structured responses.

An MCP, OpenAI tool-calling, LangGraph, or custom internal adapter should stay
thin:

```text
protocol request
  -> validate or translate protocol arguments
  -> executor.call(ToolCall(...))
  -> serialize ToolResult.to_dict()
```

Keep protocol dependencies outside the core SDK until an adapter has a concrete
consumer. That keeps `agent-sandbox` small while preserving a clear extension
point.
