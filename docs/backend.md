# Backend Boundary

Modal is the only real backend in this version. Keep that detail behind the
sandbox runner and primitive layers.

Current layering:

```text
SandboxTools / CLI
  -> primitive
  -> runner protocol
  -> ModalSandboxRunner
  -> Modal Sandbox
```

Design rules:

- Do not return Modal objects from `SandboxTools`.
- Keep Modal imports out of harness-facing code where practical.
- Use fake runners in tests instead of launching real resources.
- Add future backends by implementing the runner protocol before changing the
  public SDK.

This keeps the package Modal-backed today while leaving room for Docker or
local backends later.
