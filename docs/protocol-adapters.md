# Protocol Adapters

`SandboxToolRegistry` is the boundary to use when exposing these tools through
another protocol.

The registry already provides the pieces most adapters need:

- `list_tools()` for discovery.
- `ToolSpec.input_schema` for argument schemas.
- `call_tool(name, arguments)` for name-based dispatch.
- `ToolResult.to_dict()` for structured responses.

An MCP, OpenAI tool-calling, LangGraph, or custom internal adapter should stay
thin:

```text
protocol request
  -> validate or translate protocol arguments
  -> registry.call_tool(name, arguments)
  -> serialize ToolResult.to_dict()
```

Keep protocol dependencies outside the core SDK until an adapter has a concrete
consumer. That keeps `agent-sandbox` small while preserving a clear extension
point.
