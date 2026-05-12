# Testing Notes

Run the local test suite with:

```bash
uv run pytest
```

Default tests should avoid real Modal resources. Use fake runners and fake
sandbox objects for workflow and CLI coverage.

Before running real backend checks, verify local setup:

```bash
uv run agent-sandbox doctor
```

Real Modal integration tests are opt-in:

```bash
AGENT_SANDBOX_RUN_MODAL_TESTS=1 uv run pytest tests/test_modal_integration.py
```

Integration tests should:

- Use unique sandbox names.
- Clean up sandboxes in `finally`.
- Put generated local files under `artifacts/`.
- Stay skipped unless `AGENT_SANDBOX_RUN_MODAL_TESTS=1` is set.

Use the narrowest useful command while iterating:

```bash
uv run pytest tests/test_tools.py
uv run pytest tests/test_managed_sandbox.py
```
