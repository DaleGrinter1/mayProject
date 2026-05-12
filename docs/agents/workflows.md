# Workflow Notes

The repo has two command styles plus a Python SDK for external harnesses.

Harnesses should call `SandboxTools` directly:

```python
from agent_sandbox import SandboxToolPolicy, SandboxTools

tools = SandboxTools(
    policy=SandboxToolPolicy(allowed_tools=("shell", "python", "browser")),
)
result = tools.shell(["python", "--version"])
```

One-shot commands create temporary sandboxes for a single task:

```bash
uv run agent-sandbox-screenshot https://example.com
uv run agent-sandbox-shell python --version
uv run agent-sandbox-python ./path/to/script.py
```

Managed sandbox commands operate on named remote computers:

```bash
uv run agent-sandbox create --name devbox --image dev
uv run agent-sandbox exec --name devbox -- python --version
uv run agent-sandbox copy-to --name devbox ./script.py /workspace/script.py
uv run agent-sandbox copy-from --name devbox /tmp/result.txt artifacts/result.txt
uv run agent-sandbox logs --name devbox
uv run agent-sandbox terminate --name devbox
```

Use `artifacts/` for generated or copied-back files. Screenshots default to
`artifacts/screenshots/`.

Managed screenshots require a sandbox created with the `browser` image:

```bash
uv run agent-sandbox create --name browserbox --image browser
uv run agent-sandbox screenshot --name browserbox https://example.com
```

`agent-sandbox logs` reads stdout and stderr after a sandbox has stopped. Avoid
reading logs from a running sandbox because Modal stream reads wait for EOF.
