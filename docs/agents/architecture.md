# Architecture Notes

The project is intentionally layered:

```text
external harness / CLI
  -> SandboxTools or workflow
  -> primitive
  -> sandbox runner
  -> Modal Sandbox
```

Use this shape when adding behavior:

- `agent_sandbox/tools.py`: stable SDK surface for external agent harnesses.
- `agent_sandbox/registry.py`: dynamic discovery and name-based tool calls.
- `agent_sandbox/cli/`: argument parsing and user-facing command output.
- `agent_sandbox/cli/output.py`: shared CLI table, JSON, and status rendering.
- `agent_sandbox/workflows/`: product-level operations such as managed sandboxes.
- `agent_sandbox/primitives/`: reusable one-shot capabilities.
- `agent_sandbox/sandbox/`: Modal image, lifecycle, runner, fake runner, and shared types.

Prefer extending an existing layer before adding a new one. Keep Modal-specific
lifecycle details in `agent_sandbox/sandbox/runner.py` or the managed sandbox
workflow instead of spreading Modal calls throughout the CLI or SDK.
