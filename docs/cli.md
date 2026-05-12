# CLI

The CLI is a human/debugging layer around the same sandbox capabilities.

One-shot commands create temporary sandboxes:

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

Named sandbox administration uses the main command:

```bash
uv run agent-sandbox create --name devbox --image dev
uv run agent-sandbox exec --name devbox -- python --version
uv run agent-sandbox list --json
uv run agent-sandbox terminate --name devbox
```

Use named sandboxes for inspection and repeated manual work. Prefer the SDK or
one-shot commands for normal isolated tool calls.
