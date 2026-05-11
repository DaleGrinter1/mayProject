# mayproject

`mayproject` manages Modal sandboxes as small remote computers. It supports
one-shot commands for quick work and `may-sandbox` commands for named,
longer-lived sandboxes.

Generated files belong under `artifacts/`. Screenshots use
`artifacts/screenshots/` by default.

## Project Layout

```text
mayproject/
  cli/                         # console script entry points
  config.py                    # pyproject.toml settings
  search.py                    # search-term to URL resolution
  urls.py                      # URL helpers
  workflows/doctor.py          # local setup checks
  workflows/screenshot.py      # one-shot screenshot workflow
  workflows/sandbox.py         # named Modal sandbox workflow
  primitives/browser.py        # reusable browser sandbox primitive
  primitives/python.py         # reusable Python script/code primitive
  primitives/repo.py           # reusable clone-and-run repository primitive
  primitives/shell.py          # reusable shell command sandbox primitive
  sandbox/fake.py              # fake runner for local primitive tests
  sandbox/images.py            # Modal image definitions
  sandbox/runner.py            # Modal sandbox lifecycle and command runner
  sandbox/types.py             # Pydantic models and shared runner protocol
tests/                         # local tests plus opt-in Modal integration tests
```

Runtime dependencies are Modal for remote computers and Pydantic for shared
sandbox data models.

The intended layering is:

```text
CLI / future API / future Modal Function
  -> workflow
  -> primitive
  -> sandbox runner
  -> Modal Sandbox
```

## Configuration

Defaults live in `pyproject.toml`:

```toml
[tool.mayproject]
app_name = "my-app"
artifacts_dir = "artifacts"
```

The `--app-name` flag overrides the configured app name for `may-sandbox`
commands.

## One-Shot Commands

Use one-shot commands when you want a temporary sandbox to do one job and then
go away:

```bash
uv run may-screenshot https://example.com
uv run may-screenshot "example search term"
uv run may-shell python --version
uv run may-python ./path/to/script.py
```

`may-screenshot` screenshots a valid `http` or `https` URL directly. Otherwise,
it searches DuckDuckGo and screenshots the first result. Each run saves a PNG
and matching text observation in `artifacts/screenshots/`.

## Managed Sandboxes

Use `may-sandbox` when you want a named remote computer that can run repeated
commands, hold copied files, attach volumes, or open an interactive shell.

```bash
uv run may-sandbox doctor
uv run may-sandbox create --name devbox --image dev --volume my-volume:/workspace/data
uv run may-sandbox list
uv run may-sandbox list --watch
uv run may-sandbox status --name devbox
uv run may-sandbox inspect --name devbox
uv run may-sandbox exec --name devbox -- python --version
uv run may-sandbox logs --name devbox
uv run may-sandbox shell --name devbox
uv run may-sandbox terminate --name devbox
```

To stop every sandbox started by this project:

```bash
uv run may-sandbox terminate-all
```

## Files

Copy local files into a sandbox:

```bash
uv run may-sandbox copy-to --name devbox ./script.py /workspace/script.py
uv run may-sandbox put --name devbox ./script.py /workspace/script.py
```

Copy remote files back into `artifacts/`:

```bash
mkdir -p artifacts
uv run may-sandbox copy-from --name devbox /tmp/result.txt artifacts/result.txt
uv run may-sandbox get --id sb-... /tmp/result.txt artifacts/result.txt
```

`put` is an alias for `copy-to`; `get` is an alias for `copy-from`.

## Screenshots

Run a screenshot in a new temporary sandbox:

```bash
uv run may-screenshot https://example.com
```

Run a screenshot inside an existing managed sandbox:

```bash
uv run may-sandbox create --name browserbox --image browser
uv run may-sandbox screenshot --name browserbox https://example.com
uv run may-sandbox screenshot --id sb-... "example search term"
```

Managed screenshots need a sandbox created with the `browser` image because
they use Playwright and Chromium.

Choose a different local output folder:

```bash
uv run may-sandbox screenshot --name browserbox --output-dir artifacts/custom-shots https://example.com
```

## Structured Output

Use `--json` with commands that describe sandboxes:

```bash
uv run may-sandbox list --json
uv run may-sandbox status --name devbox --json
uv run may-sandbox inspect --id sb-... --json
```

This is useful for scripts and future automation.

## Logs

Read stdout and stderr from a sandbox after its root process has stopped:

```bash
uv run may-sandbox logs --name devbox
uv run may-sandbox logs --id sb-...
```

Logs are only read after a sandbox has stopped because Modal's stream reads wait
for EOF. For command output while a sandbox is running, use `may-sandbox exec`.

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
Pydantic models, config loading, and fake-runner behavior without launching
Modal sandboxes.

Run the opt-in real Modal integration tests:

```bash
MAYPROJECT_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_integration.py
```

Those tests create real sandboxes, copy files in and out through `artifacts/`,
and terminate the sandboxes afterward.
