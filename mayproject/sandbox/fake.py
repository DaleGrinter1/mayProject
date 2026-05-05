from collections.abc import Callable
from pathlib import Path

from mayproject.sandbox.types import CommandResult, SandboxHandle, SandboxSpec


class FakeSandboxRunner:
    """Pretends to be a remote computer during tests."""

    def __init__(
        self,
        spec: SandboxSpec,
        command_handler: Callable[[tuple[str, ...]], CommandResult] | None = None,
    ) -> None:
        self.spec = spec
        self.command_handler = command_handler
        self.writes: list[tuple[str, str]] = []
        self.copied_from_local: list[tuple[Path, str]] = []
        self.copied_to_local: list[tuple[str, Path]] = []
        self.commands: list[tuple[str, ...]] = []
        self.closed = False
        self.terminated = False

    def __enter__(self) -> "FakeSandboxRunner":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.terminated = self.spec.terminate_on_exit
        self.closed = True

    def write_text(self, content: str, remote_path: str) -> None:
        self.writes.append((content, remote_path))

    def copy_from_local(self, local_path: Path, remote_path: str) -> None:
        self.copied_from_local.append((local_path, remote_path))

    def copy_to_local(self, remote_path: str, local_path: Path) -> None:
        self.copied_to_local.append((remote_path, local_path))

    def exec(self, *command: str) -> CommandResult:
        self.commands.append(command)
        if self.command_handler is not None:
            return self.command_handler(command)
        return CommandResult(returncode=0, stdout="", stderr="")

    def handle(self) -> SandboxHandle:
        return SandboxHandle(
            object_id=f"fake-{self.spec.name or 'sandbox'}",
            app_name=self.spec.app_name,
            name=self.spec.name,
            tags=self.spec.tags,
            returncode=None,
        )
