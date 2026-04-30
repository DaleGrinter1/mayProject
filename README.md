# mayproject

Create a Modal sandbox that opens a URL with Playwright/Chromium and copies a
screenshot and text observation back into the local `screenshots/` folder.

## Project structure

The project is now split into a small package so sandbox behavior can scale
without keeping everything in one script:

```text
screenshot.py                  # thin CLI entry point
mayproject/
  search.py                    # search-term to URL resolution
  urls.py                      # URL helpers
  workflows/screenshot.py      # product-level screenshot workflow
  primitives/browser.py        # reusable browser sandbox primitive
  primitives/shell.py          # reusable shell command sandbox primitive
  primitives/scripts/          # scripts copied into sandbox filesystems
  sandbox/images.py            # Modal image definitions
  sandbox/runner.py            # Modal sandbox lifecycle and command runner
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

## Usage

```bash
uv run python screenshot.py https://example.com
uv run python screenshot.py "example search term"
```

`screenshot.py` screenshots the input directly when it is a valid `http` or
`https` URL. Otherwise, it searches DuckDuckGo and screenshots the first result.
Each run saves a `.png` screenshot and a matching `.txt` file with the page URL,
title, visible text, links, and buttons.

The first run may take longer while Modal builds the sandbox image.
