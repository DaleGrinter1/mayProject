# OpenAI Agents SDK Compatibility Plan

The goal is to let `agent-sandbox` work naturally with the OpenAI Agents SDK
while keeping this package focused on safe sandbox execution. The right shape is
a thin adapter around `SandboxToolExecutor`, not a rewrite of the sandbox core.

Current repo fit:

- `SandboxToolExecutor` already provides a stable tool-call envelope.
- `SandboxToolRegistry` already exposes tool discovery and JSON-style schemas.
- `ToolResult.to_dict()` already provides structured tool outputs.
- Policy checks, fake tools, audit logging, and Modal-backed execution already
  live behind the SDK surface.

OpenAI documentation points to two useful integration styles:

- Custom Python function tools for Agents SDK agents.
- MCP or other external tool servers for protocol-based integrations.

Official references used while drafting this plan:

- `https://developers.openai.com/api/docs/libraries#use-the-agents-sdk`
- `https://developers.openai.com/cookbook/examples/agents_sdk/multi-agent-portfolio-collaboration/multi_agent_portfolio_collaboration#supported-tool-types`

## Phase 1: Learn The Required Surface

Study the current OpenAI Agents SDK docs and examples before implementing the
adapter.

Required topics:

- `Agent`
- `Runner.run`
- `function_tool`
- tool return value expectations
- sync vs async tool functions
- tool schema generation and validation
- tracing behavior
- guardrail behavior
- dependency/package name for the Python Agents SDK

Implementation notes to capture:

- Whether tool functions may return dictionaries directly.
- How exceptions inside tools are surfaced to the agent loop.
- Whether the SDK supports explicit tool schemas or only inferred schemas.
- Whether dynamic tool generation is stable enough for all registry tools.
- Whether tracing should be configured by this package or left to the caller.

Deliverable:

- Add a short research note to this file or `docs/openai-agents-sdk.md`
  summarizing exact SDK APIs, imports, and package names discovered.

## Phase 2: Build A Minimal Adapter

Add a module such as `agent_sandbox/adapters/openai_agents.py`.

The adapter should expose one public helper:

```python
create_openai_agent_tools(executor: SandboxToolExecutor) -> list[object]
```

The helper should return OpenAI Agents SDK-compatible function tools wrapping
the current registry tools:

- `sandbox_shell`
- `sandbox_python_code`
- `sandbox_python_script`
- `sandbox_screenshot`

Each wrapper should:

- Accept normal Python arguments matching the registry schema.
- Build a `ToolCall`.
- Call `SandboxToolExecutor.call(...)`.
- Return `ToolResult.to_dict()`.
- Preserve `call_id`, `agent_id`, `task_id`, and metadata when the SDK makes
  those values available.

Keep the adapter thin. Do not move policy, audit, Modal, or fake-runner behavior
into the OpenAI-specific module.

## Phase 3: Keep OpenAI Optional

The OpenAI Agents SDK should be an optional dependency.

Expected dependency shape:

```bash
uv add --optional openai-agents <verified-package-name>
```

Implementation requirements:

- Importing `agent_sandbox` must not require OpenAI packages.
- Importing `agent_sandbox.adapters.openai_agents` may require the optional
  dependency.
- If the optional dependency is missing, raise an `ImportError` with the exact
  install command.
- Do not add OpenAI credentials or API-key handling to core SDK objects.

## Phase 4: Add An Example Agent

Add `examples/openai_agents_sdk_agent.py`.

The example should:

- Create a conservative `SandboxToolPolicy`.
- Create `SandboxTools`, `SandboxToolRegistry`, and `SandboxToolExecutor`.
- Convert executor-backed tools into OpenAI Agents SDK tools.
- Create a minimal `Agent`.
- Run a simple prompt through `Runner.run`.
- Print the final response and tool result artifacts.

Start with one real sandbox tool:

- `sandbox_shell`

Then expand to:

- `sandbox_python_code`
- `sandbox_python_script`
- `sandbox_screenshot`

Example execution should be opt-in and require `OPENAI_API_KEY`.

## Phase 5: Add Tests

Unit tests should not call OpenAI or Modal.

Required unit tests:

- Adapter returns one OpenAI-compatible tool per allowed registry tool.
- Each wrapper calls `SandboxToolExecutor.call(...)`.
- Each wrapper returns `ToolResult.to_dict()`.
- Policy denial returns a structured failed result.
- Invalid arguments return a structured failed result when possible.
- Importing core `agent_sandbox` works without OpenAI dependencies installed.
- Missing optional dependency produces a clear `ImportError`.

Optional integration tests should be skipped by default.

Recommended environment flag:

```bash
AGENT_SANDBOX_RUN_OPENAI_TESTS=1
```

OpenAI integration command:

```bash
AGENT_SANDBOX_RUN_OPENAI_TESTS=1 uv run pytest tests/test_openai_agents_integration.py
```

Full end-to-end Modal plus OpenAI validation should require both flags:

```bash
AGENT_SANDBOX_RUN_OPENAI_TESTS=1 \
AGENT_SANDBOX_RUN_MODAL_TESTS=1 \
uv run pytest tests/test_openai_agents_integration.py tests/test_modal_integration.py
```

## Phase 6: Add Documentation

Add `docs/openai-agents-sdk.md`.

The doc should explain:

- What the adapter does.
- How to install the optional dependency.
- How to configure policy.
- How to create executor-backed OpenAI tools.
- How to run the example agent.
- How to run unit tests.
- How to run opt-in OpenAI integration tests.
- Why fake tools should be used for normal local tests.

Architecture description:

```text
OpenAI Agent
  -> OpenAI function tool
  -> agent-sandbox OpenAI adapter
  -> SandboxToolExecutor
  -> SandboxToolRegistry
  -> SandboxTools
  -> Modal sandbox or fake primitive
```

## Recommended First Slice

Implement the smallest useful path first:

1. Verify current OpenAI Agents SDK package name and function-tool API.
2. Add optional dependency metadata.
3. Add `agent_sandbox/adapters/openai_agents.py`.
4. Implement `sandbox_shell` only.
5. Add unit tests with fake executor/tools.
6. Add `examples/openai_agents_sdk_agent.py` for `sandbox_shell`.
7. Run `uv run pytest`.

After that slice passes, add the remaining tools:

- `sandbox_python_code`
- `sandbox_python_script`
- `sandbox_screenshot`

## Non-Goals For The First Adapter

- Do not build a full agent framework inside this repo.
- Do not make OpenAI a required runtime dependency.
- Do not replace `SandboxToolExecutor`.
- Do not mix OpenAI tracing concerns into core sandbox execution.
- Do not run Modal-backed or OpenAI-backed tests by default.

## Acceptance Criteria

The adapter is ready when:

- Existing local tests still pass with `uv run pytest`.
- `import agent_sandbox` works without OpenAI dependencies installed.
- OpenAI adapter unit tests pass without API credentials.
- The example agent can run with `OPENAI_API_KEY` and optional dependencies.
- Tool calls still return normal `ToolResult.to_dict()` payloads.
- Policy failures remain visible as structured failed results.
