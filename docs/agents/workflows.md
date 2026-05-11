# Workflow Notes

The repo has two command styles.

One-shot commands create temporary sandboxes for a single task:

```bash
uv run may-screenshot https://example.com
uv run may-shell python --version
uv run may-python ./path/to/script.py
```

Agent workflow commands run registered local agents:

```bash
uv run may-agent list
uv run may-agent run "Package the agent API"
uv run may-agent run --agent echo --input audience=agent-authors "Package the agent API"
```

Workflow agents receive sandbox-backed tools through `context.capabilities`.
Agents declare the tools they need with `allowed_primitives`, and the context
checks that declaration before running shell, Python, or browser work.

Managed sandbox commands operate on named remote computers:

```bash
uv run may-sandbox create --name devbox --image dev
uv run may-sandbox exec --name devbox -- python --version
uv run may-sandbox copy-to --name devbox ./script.py /workspace/script.py
uv run may-sandbox copy-from --name devbox /tmp/result.txt artifacts/result.txt
uv run may-sandbox logs --name devbox
uv run may-sandbox terminate --name devbox
```

Use `artifacts/` for generated or copied-back files. Screenshots default to
`artifacts/screenshots/`.

Managed screenshots require a sandbox created with the `browser` image:

```bash
uv run may-sandbox create --name browserbox --image browser
uv run may-sandbox screenshot --name browserbox https://example.com
```

`may-sandbox logs` reads stdout and stderr after a sandbox has stopped. Avoid
reading logs from a running sandbox because Modal stream reads wait for EOF.
