# Security Notes

`agent-sandbox` helps isolate tool execution, but it does not make arbitrary
agent actions safe by itself. The harness still needs to decide what an agent is
allowed to do.

## Responsibilities

The harness should:

- Grant only the tools needed for the current task.
- Use `SandboxToolPolicy` guardrails for shell commands, browser domains, and
  timeouts when possible.
- Avoid passing secrets into untrusted agent-generated code.
- Treat stdout, stderr, screenshots, and copied files as potentially sensitive.
- Terminate managed sandboxes when work is complete.
- Keep Modal credentials scoped to the environment that needs them.

This package should:

- Keep Modal details behind the runner and primitive layers.
- Return structured results instead of exposing backend objects through the SDK.
- Preserve artifacts and run records in predictable local paths.
- Fail clearly when policy blocks a call or Modal setup is missing.

## Tool Boundaries

`allowed_tools` is the first boundary. Optional policy fields add narrower
controls:

```python
SandboxToolPolicy(
    allowed_tools=("shell", "screenshot"),
    allowed_shell_commands=("python", "pytest"),
    allowed_browser_domains=("example.com",),
    allowed_python_script_roots=("scripts",),
    max_timeout=60,
)
```

These checks happen before a sandbox starts.

## Secrets

Do not pass production credentials, personal data, or long-lived tokens into
agent-generated commands unless the harness deliberately scopes and audits that
access. Run records and artifacts may persist local copies of command output,
errors, screenshots, or metadata.

## Managed Sandboxes

Managed sandboxes are useful for debugging and repeated work, but they are more
persistent than one-shot SDK calls. Prefer temporary SDK calls for normal agent
tools. Use:

```bash
uv run agent-sandbox terminate --name devbox
uv run agent-sandbox terminate-all
```

when a managed session is finished.
