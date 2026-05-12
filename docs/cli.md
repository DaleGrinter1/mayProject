# CLI

The CLI is a human/debugging layer around the same sandbox capabilities.

## Setup

Install dependencies before running commands:

```bash
uv sync
```

Check Modal setup and authentication:

```bash
uv run agent-sandbox doctor
```

If the doctor command reports missing auth, log in with:

```bash
uv run modal token new
```

## One-Shot Commands

One-shot commands create temporary sandboxes for a single task and then let
them go away:

```bash
uv run agent-sandbox-shell -- python --version
uv run agent-sandbox-python ./script.py
uv run agent-sandbox-screenshot https://example.com
```

Each one-shot command supports structured output:

```bash
uv run agent-sandbox-shell --json -- python --version
uv run agent-sandbox-python --json ./script.py
uv run agent-sandbox-screenshot --json https://example.com
```

Add `--record-run` to write `.agent-sandbox/runs/.../result.json` and stream
files for debugging.

Use one-shot commands for normal isolated tool calls and quick local
verification.

## Managed Sandboxes

Named sandbox administration uses the main command:

```bash
uv run agent-sandbox create --name devbox --image dev
uv run agent-sandbox exec --name devbox -- python --version
uv run agent-sandbox list --json
uv run agent-sandbox terminate --name devbox
```

Use named sandboxes for inspection and repeated manual work. Prefer the SDK or
one-shot commands for normal isolated tool calls.

Browser screenshots in managed sandboxes require a sandbox created with the
`browser` image:

```bash
uv run agent-sandbox create --name browserbox --image browser
uv run agent-sandbox screenshot --name browserbox https://example.com
uv run agent-sandbox terminate --name browserbox
```

## Artifacts

Generated files belong under `artifacts/`. Screenshot files default to
`artifacts/screenshots/`.

When using `copy-from` or `get`, copy remote files back into `artifacts/` unless
there is a specific reason to place them elsewhere:

```bash
uv run agent-sandbox copy-from --name devbox /tmp/result.txt artifacts/result.txt
```
