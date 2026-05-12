# agent-sandbox

`agent-sandbox` is a Modal-backed sandbox tool provider for agent harnesses.
It gives another project a small Python API for running isolated per-task work,
plus CLI commands for local debugging and named sandbox administration.

Generated files belong under `artifacts/`. Screenshots use
`artifacts/screenshots/` by default.

## Tool Provider Contract

External harnesses should import the stable SDK surface from `agent_sandbox`:

```python
from pathlib import Path

from agent_sandbox import SandboxToolPolicy, SandboxTools

tools = SandboxTools(
    app_name="my-app",
    policy=SandboxToolPolicy(allowed_tools=("shell", "python", "browser")),
)

shell_result = tools.shell(["python", "--version"])
code_result = tools.python_code("print('hello')")
script_result = tools.python_script(Path("script.py"))
shot_result = tools.screenshot("https://example.com")
```

Each tool call returns a structured result with `status`, `returncode`,
`stdout`, `stderr`, `artifacts`, `metadata`, and `error`. SDK calls create
temporary per-task sandboxes by default. The harness owns orchestration,
memory, planning, and agent policy; this package owns sandbox execution.

## Project Layout

```text
agent_sandbox/
  tools.py                     # stable SDK for external harnesses
  cli/                         # console script entry points
  config.py                    # pyproject.toml settings
  search.py                    # search-term to URL resolution
  urls.py                      # URL helpers
  workflows/doctor.py          # local setup checks
  workflows/screenshot.py      # screenshot workflow helpers
  workflows/sandbox.py         # named Modal sandbox workflow
  primitives/                  # reusable one-shot sandbox capabilities
  sandbox/                     # Modal image, lifecycle, fake runner, types
tests/                         # local tests plus opt-in Modal integration tests
```

Runtime dependencies are Modal for remote computers and Pydantic for shared
sandbox data models.

The intended layering is:

```text
external harness / CLI
  -> SandboxTools or workflow
  -> primitive
  -> sandbox runner protocol
  -> Modal Sandbox
```

## Configuration

Defaults live in `pyproject.toml`:

```toml
[tool.agent-sandbox]
app_name = "my-app"
artifacts_dir = "artifacts"
```

The `--app-name` flag overrides the configured app name for `agent-sandbox`
managed sandbox commands.

## One-Shot Commands

Use one-shot commands when you want a temporary sandbox to do one job and then
go away:

```bash
uv run agent-sandbox-screenshot https://example.com
uv run agent-sandbox-screenshot "example search term"
uv run agent-sandbox-shell python --version
uv run agent-sandbox-python ./path/to/script.py
```

`agent-sandbox-screenshot` screenshots a valid `http` or `https` URL directly.
Otherwise, it searches DuckDuckGo and screenshots the first result.

## Managed Sandboxes

Use `agent-sandbox` when you want a named remote computer for debugging,
interactive work, copied files, attached volumes, or repeated commands.
Harness-facing SDK calls should normally use temporary per-task sandboxes
instead.

```bash
uv run agent-sandbox doctor
uv run agent-sandbox create --name devbox --image dev --volume my-volume:/workspace/data
uv run agent-sandbox list
uv run agent-sandbox list --watch
uv run agent-sandbox status --name devbox
uv run agent-sandbox inspect --name devbox
uv run agent-sandbox exec --name devbox -- python --version
uv run agent-sandbox logs --name devbox
uv run agent-sandbox shell --name devbox
uv run agent-sandbox terminate --name devbox
```

To stop every sandbox started by this project:

```bash
uv run agent-sandbox terminate-all
```

## Files And Screenshots

Copy local files into a sandbox:

```bash
uv run agent-sandbox copy-to --name devbox ./script.py /workspace/script.py
uv run agent-sandbox put --name devbox ./script.py /workspace/script.py
```

Copy remote files back into `artifacts/`:

```bash
mkdir -p artifacts
uv run agent-sandbox copy-from --name devbox /tmp/result.txt artifacts/result.txt
uv run agent-sandbox get --id sb-... /tmp/result.txt artifacts/result.txt
```

Run a screenshot inside an existing managed sandbox:

```bash
uv run agent-sandbox create --name browserbox --image browser
uv run agent-sandbox screenshot --name browserbox https://example.com
uv run agent-sandbox screenshot --id sb-... "example search term"
```

Managed screenshots need a sandbox created with the `browser` image because
they use Playwright and Chromium.

## Structured Output

Use `--json` with commands that describe sandboxes:

```bash
uv run agent-sandbox list --json
uv run agent-sandbox status --name devbox --json
uv run agent-sandbox inspect --id sb-... --json
```

This is useful for scripts and future automation.

## Images

Available sandbox images:

- `python`: a small Python 3.13 image.
- `browser`: the Python image with Playwright and Chromium.
- `dev`: the Python image with everyday coding tools like `git`, `curl`, and `uv`.

The first run may take longer while Modal builds each sandbox image.

## Testing

Run the local test suite:

```bash
uv run pytest
```

The default tests validate parsing, workflow composition, primitive commands,
structured SDK results, Pydantic models, config loading, and fake-runner
behavior without launching Modal sandboxes.

Run the opt-in real Modal integration tests:

```bash
AGENT_SANDBOX_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_integration.py
```

Those tests create real sandboxes, copy files in and out through `artifacts/`,
and terminate the sandboxes afterward.
