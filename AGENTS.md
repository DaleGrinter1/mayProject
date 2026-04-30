# AGENTS.md

## Project Overview

- This is a Python project named `mayproject`.
- The package metadata lives in `pyproject.toml`.
- Python is pinned to 3.13 via `.python-version` and `requires-python = ">=3.13,<3.14"`.
- Dependencies are managed with `uv`; keep `uv.lock` in sync when dependencies change.

## Working Agreements

- Prefer small, focused changes that match the current project structure.
- Check existing files before adding new conventions or tools.
- Do not add runtime dependencies unless they are needed for the requested work.
- Keep generated or exploratory files out of the repository unless the task calls for them.

## Common Commands

- Run the app, once an entry point exists: `uv run python main.py`
- Add a dependency: `uv add <package>`
- Add a development dependency: `uv add --dev <package>`
- Sync the environment: `uv sync`

## Testing and Validation

- If tests are added later, document the test command here.
- When changing Python code, run the narrowest useful validation command available.
- If no tests or executable entry point exist yet, say that clearly in the final response.

## Documentation

- Keep `README.md` aligned with the actual project behavior.
- Document setup steps when adding dependencies, commands, or environment variables.

## Codex Notes

- This file follows OpenAI Codex's `AGENTS.md` project-instructions convention.
- More specific `AGENTS.md` or `AGENTS.override.md` files may be added in subdirectories later if part of the project needs different guidance.
