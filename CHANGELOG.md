# Changelog

## 0.1.0 - Unreleased

- Rename the package to `agent-sandbox` with import package `agent_sandbox`.
- Add `SandboxTools`, `SandboxToolPolicy`, and `ToolResult` as the public SDK.
- Add structured JSON output for one-shot CLI commands.
- Add optional per-tool-call run recording under `.agent-sandbox/runs/`.
- Keep Modal as the only real backend behind the runner layer.
- Remove the older bundled mini-agent workflow code.
