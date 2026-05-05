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
  workflows/screenshot.py      # product-level screenshot workflow
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

## Usage

```bash
uv run python screenshot.py https://example.com
uv run python screenshot.py "example search term"
uv run may-screenshot https://example.com
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
