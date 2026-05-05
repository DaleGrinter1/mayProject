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

- Screenshot a URL: `uv run may-screenshot https://example.com`
- Run a command in a sandbox: `uv run may-shell python --version`
- Run a local Python script in a sandbox: `uv run may-python ./path/to/script.py`
- Add a dependency: `uv add <package>`
- Add a development dependency: `uv add --dev <package>`
- Sync the environment: `uv sync`

## Testing and Validation

- Run tests: `uv run pytest`
- When changing Python code, run the narrowest useful validation command available.

## Documentation

- Keep `README.md` aligned with the actual project behavior.
- Document setup steps when adding dependencies, commands, or environment variables.

## Additional Agent Context

- Longer context for agents lives in `docs/agents/`.
- Start with `docs/agents/README.md` when a task needs more background.
- Use `docs/agents/architecture.md` for layering and ownership guidance.
- Use `docs/agents/workflows.md` for command behavior and user-facing flows.
- Use `docs/agents/testing.md` for local and opt-in Modal validation guidance.

## Codex Notes

- This file follows OpenAI Codex's `AGENTS.md` project-instructions convention.
- More specific `AGENTS.md` or `AGENTS.override.md` files may be added in subdirectories later if part of the project needs different guidance.
