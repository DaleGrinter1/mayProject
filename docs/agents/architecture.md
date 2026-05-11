# Architecture Notes

The project is intentionally layered:

```text
CLI / future API / future Modal Function
  -> workflow
  -> primitive
  -> sandbox runner
  -> Modal Sandbox
```

Use this shape when adding behavior:

- `mayproject/cli/`: argument parsing and user-facing command output.
- `mayproject/cli/output.py`: shared CLI table, JSON, and status rendering.
- `mayproject/workflows/`: product-level operations such as managed sandboxes.
- `mayproject/primitives/`: reusable one-shot capabilities.
- `mayproject/sandbox/`: Modal image, lifecycle, runner, fake runner, and shared types.

Prefer extending an existing layer before adding a new one. Keep Modal-specific
lifecycle details in `mayproject/sandbox/runner.py` or the managed sandbox
workflow instead of spreading Modal calls throughout the CLI.
