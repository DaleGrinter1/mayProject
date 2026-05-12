from collections.abc import Callable
from pathlib import Path

from agent_sandbox.sandbox.types import CommandResult, SandboxHandle, SandboxSpec


class FakeSandboxRunner:
    """Pretends to be a remote computer during tests.

    Attributes:
        spec: The remote computer instructions.
        command_handler: Optional test code that returns command results.
    """

    def __init__(
        self,
        spec: SandboxSpec,
        command_handler: Callable[[tuple[str, ...]], CommandResult] | None = None,
    ) -> None:
        # Keep simple lists so tests can inspect what would have happened.
        self.spec = spec
        self.command_handler = command_handler
        self.writes: list[tuple[str, str]] = []
        self.copied_from_local: list[tuple[Path, str]] = []
        self.copied_to_local: list[tuple[str, Path]] = []
        self.commands: list[tuple[str, ...]] = []
        self.closed = False
        self.terminated = False

    def __enter__(self) -> "FakeSandboxRunner":
        # Tests use this like the real remote computer runner.
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        # Tests can check whether the fake computer would have closed.
        self.terminated = self.spec.terminate_on_exit
        self.closed = True

    def write_text(self, content: str, remote_path: str) -> None:
        """Records text that would be written remotely.

        Args:
            content: The text that would be written.
            remote_path: Where it would be written remotely.
        """

        self.writes.append((content, remote_path))

    def copy_from_local(self, local_path: Path, remote_path: str) -> None:
        """Records a local file copy into the fake computer.

        Args:
            local_path: The local file path.
            remote_path: Where it would be placed remotely.
        """

        self.copied_from_local.append((local_path, remote_path))

    def copy_to_local(self, remote_path: str, local_path: Path) -> None:
        """Records a remote file copy back to this computer.

        Args:
            remote_path: The remote file path.
            local_path: Where it would be saved locally.
        """

        self.copied_to_local.append((remote_path, local_path))

    def exec(self, *command: str) -> CommandResult:
        """Records a command that would run remotely.

        Args:
            *command: The command and its arguments.

        Returns:
            The fake command result.
        """

        self.commands.append(command)
        if self.command_handler is not None:
            return self.command_handler(command)
        return CommandResult(returncode=0, stdout="", stderr="")

    def handle(self) -> SandboxHandle:
        """Returns a fake name and ID for tests.

        Returns:
            Fake remote computer details.
        """

        return SandboxHandle(
            object_id=f"fake-{self.spec.name or 'sandbox'}",
            app_name=self.spec.app_name,
            name=self.spec.name,
            tags=self.spec.tags,
            returncode=None,
        )
