# mayproject

Create a Modal sandbox that opens a URL with Playwright/Chromium and copies a
screenshot and text observation back into the local `screenshots/` folder.

## Project structure

The project is now split into a small package so sandbox behavior can scale
without keeping everything in one script:

```text
screenshot.py                  # thin CLI entry point
mayproject/
  cli/                         # console script entry points
  search.py                    # search-term to URL resolution
  urls.py                      # URL helpers
  workflows/doctor.py          # local setup checks
  workflows/screenshot.py      # product-level screenshot workflow
  workflows/sandbox.py         # named Modal sandbox workflow
  primitives/browser.py        # reusable browser sandbox primitive
  primitives/python.py         # reusable Python script/code primitive
  primitives/repo.py           # reusable clone-and-run repository primitive
  primitives/shell.py          # reusable shell command sandbox primitive
  primitives/scripts/          # scripts copied into sandbox filesystems
  sandbox/fake.py              # fake runner for local primitive tests
  sandbox/images.py            # Modal image definitions
  sandbox/runner.py            # Modal sandbox lifecycle and command runner
  sandbox/types.py             # shared runner protocol and result types
tests/                         # local tests that avoid remote Modal resources
```

The intended layering is:

```text
CLI / future API / future Modal Function
  -> workflow
  -> primitive
  -> sandbox runner
  -> Modal Sandbox
```

This keeps Modal-specific lifecycle code in one place while allowing new
primitives, such as Python execution or repository test runners, to reuse the
same sandbox runner.

## Primitives

The current primitive set is:

- `BrowserPrimitive`: captures a page screenshot and text observation with Playwright.
- `ShellPrimitive`: runs a command in a Python Modal sandbox.
- `PythonPrimitive`: copies or writes Python code into a sandbox and runs it.
- `RepoPrimitive`: clones a git repository and runs a command inside it.

Primitives accept an injectable runner factory, so tests can use
`FakeSandboxRunner` without creating Modal resources.

## Managed sandbox prototype

`may-sandbox` manages a named Modal Sandbox as a small remote computer. It can
start the sandbox with a package image, attach Modal Volumes, run commands,
open Modal's interactive shell, and stop the sandbox when finished.

Quickstart:

```bash
uv run may-sandbox doctor
uv run may-sandbox create --name devbox --image dev --volume my-volume:/workspace/data
uv run may-sandbox list
uv run may-sandbox list --watch
uv run may-sandbox status --name devbox
uv run may-sandbox exec --name devbox -- python --version
uv run may-sandbox shell --name devbox
uv run may-sandbox terminate --name devbox
```

To stop every sandbox started by this project:

```bash
uv run may-sandbox terminate-all
```

Volumes use the `volume-name:/absolute/mount/path` format. Missing volumes are
created with `modal.Volume.from_name(..., create_if_missing=True)`.

Available images:

- `python`: a small Python 3.13 image.
- `browser`: the Python image with Playwright and Chromium.
- `dev`: the Python image with everyday coding tools like `git`, `curl`, and `uv`.

## Usage

```bash
uv run python screenshot.py https://example.com
uv run python screenshot.py "example search term"
uv run may-screenshot https://example.com
uv run may-sandbox doctor
uv run may-sandbox create --name devbox --image dev --volume my-volume:/workspace/data
uv run may-sandbox list
uv run may-sandbox list --watch --interval 5
uv run may-sandbox exec --name devbox -- git --version
uv run may-sandbox shell --name devbox
uv run may-sandbox terminate-all
uv run may-shell python --version
uv run may-python ./path/to/script.py
```

`screenshot.py` screenshots the input directly when it is a valid `http` or
`https` URL. Otherwise, it searches DuckDuckGo and screenshots the first result.
Each run saves a `.png` screenshot and a matching `.txt` file with the page URL,
title, visible text, links, and buttons.

The first run may take longer while Modal builds the sandbox image.

## Testing

```bash
uv run pytest
```

The current tests validate local parsing, workflow composition, primitive
commands, and fake-runner behavior without launching Modal sandboxes.
