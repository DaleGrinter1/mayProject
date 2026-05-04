# mayproject

`mayproject` is a local-first Python toolkit for coordinating agent-friendly
task sandboxes. Version 1 is intentionally small: trusted local Python callers
define workflow tasks and agent roles, agents use typed primitives, and Modal
provides the actual sandbox isolation.

The current layers are:

- Workflow orchestration: define a task, assign agent roles, run role handlers,
  and write an auditable workflow trace.
- Browser capture primitive: open a URL in Playwright/Chromium, save a
  screenshot, and save a text observation.
- Shell command primitive: run a command in a Modal sandbox and capture stdout,
  stderr, return code, metadata, and artifacts.

Each workflow creates a run directory under `.mayproject/runs/`:

```text
.mayproject/runs/<timestamp>-workflow-<objective-slug>-<short-id>/
  workflow.json
  events.jsonl
  agents/
    <agent-id>/
```

Each sandbox call also creates a run directory under `.mayproject/runs/`:

```text
.mayproject/runs/<timestamp>-<task-kind>-<short-id>/
  metadata.json
  result.json
  ...task artifacts...
```

`.mayproject/` is ignored by Git because it contains local run output.

## Project structure

```text
screenshot.py                  # thin CLI entry point for browser capture
mayproject/
  agents/base.py               # agent specs and typed outcomes
  search.py                    # search-term to URL resolution
  urls.py                      # URL helpers
  workflows/coordinator.py     # sequential coordinator for agent handlers
  workflows/state.py           # task, workflow, agent-run, and event models
  workflows/screenshot.py      # compatibility workflow over BrowserPrimitive
  primitives/browser.py        # browser capture primitive and result type
  primitives/shell.py          # shell command primitive and result type
  primitives/scripts/          # scripts copied into sandbox filesystems
  sandbox/images.py            # Modal image definitions
  sandbox/results.py           # shared run, artifact, and result models
  sandbox/runner.py            # Modal sandbox lifecycle and command runner
```

The intended layering is:

```text
CLI / local scripts
  -> workflow coordinator
  -> agent role handlers
  -> primitives
  -> sandbox runner
  -> Modal Sandbox
```

## Python API

```python
from mayproject.agents import AgentOutcome, AgentSpec
from mayproject.primitives.browser import BrowserPrimitive
from mayproject.primitives.shell import ShellPrimitive
from mayproject.workflows import AutomationTask, WorkflowCoordinator

task = AutomationTask("Research example.com and capture evidence")
agents = (
    AgentSpec("researcher", "Researcher", allowed_primitives=("browser",)),
    AgentSpec("verifier", "Verifier", allowed_primitives=("shell",)),
)

def researcher(context):
    browser_result = BrowserPrimitive().capture_page("https://example.com")
    return AgentOutcome(
        "succeeded",
        output={"url": browser_result.url},
        sandbox_runs=(browser_result.run,),
    )

def verifier(context):
    shell_result = ShellPrimitive().run(("python", "--version"))
    return AgentOutcome(
        "succeeded" if shell_result.returncode == 0 else "failed",
        output={"returncode": shell_result.returncode},
        sandbox_runs=(shell_result.run,),
    )

workflow = WorkflowCoordinator(agents).run(
    task,
    {"researcher": researcher, "verifier": verifier},
)
print(workflow.status)
print(workflow.artifact_dir)
```

Primitives can also be called directly:

```python
from mayproject.primitives.browser import BrowserPrimitive
from mayproject.primitives.shell import ShellPrimitive

browser_result = BrowserPrimitive().capture_page("https://example.com")
print(browser_result.status)
print(browser_result.image_path)
print(browser_result.text_path)
print(browser_result.run.artifact_dir)

shell_result = ShellPrimitive().run(("python", "--version"))
print(shell_result.returncode)
print(shell_result.stdout)
print(shell_result.run.artifact_dir)
```

The public API is still local and method-oriented in v1. There is no HTTP
server, LLM provider integration, task registry, auth layer, quota system, or
database yet.

## CLI usage

```bash
uv run python screenshot.py https://example.com
uv run python screenshot.py "example search term"
```

`screenshot.py` screenshots the input directly when it is a valid `http` or
`https` URL. Otherwise, it searches DuckDuckGo and screenshots the first result.
The first Modal browser run may take longer while Modal builds the image.

## Validation

Pure local tests do not require Modal:

```bash
uv run python -m unittest
```

Modal integration is manual for now:

```bash
uv run python screenshot.py https://example.com
```
