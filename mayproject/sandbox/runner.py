from dataclasses import dataclass, field
from pathlib import Path

import modal


@dataclass(frozen=True)
class SandboxSpec:
    app_name: str = "my-app"
    command: tuple[str, ...] = ("sleep", "300")
    image: modal.Image | None = None
    timeout: int = 600
    idle_timeout: int = 120
    verbose: bool = True
    tags: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class ModalSandboxRunner:
    def __init__(self, spec: SandboxSpec) -> None:
        self.spec = spec
        self._sandbox: modal.Sandbox | None = None

    def __enter__(self) -> "ModalSandboxRunner":
        app = modal.App.lookup(self.spec.app_name, create_if_missing=True)
        create_kwargs = {
            "app": app,
            "timeout": self.spec.timeout,
            "idle_timeout": self.spec.idle_timeout,
            "verbose": self.spec.verbose,
        }
        if self.spec.image is not None:
            create_kwargs["image"] = self.spec.image

        self._sandbox = modal.Sandbox.create(
            *self.spec.command,
            **create_kwargs,
        )
        if self.spec.tags:
            self._sandbox.set_tags(self.spec.tags)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._sandbox is None:
            return

        try:
            self._sandbox.terminate()
        finally:
            self._sandbox.detach()
            self._sandbox = None

    @property
    def sandbox(self) -> modal.Sandbox:
        if self._sandbox is None:
            raise RuntimeError("Sandbox runner must be used as a context manager")
        return self._sandbox

    def write_text(self, content: str, remote_path: str) -> None:
        self.sandbox.filesystem.write_text(content, remote_path)

    def copy_from_local(self, local_path: Path, remote_path: str) -> None:
        self.sandbox.filesystem.copy_from_local(local_path, remote_path)

    def copy_to_local(self, remote_path: str, local_path: Path) -> None:
        self.sandbox.filesystem.copy_to_local(remote_path, local_path)

    def exec(self, *command: str) -> CommandResult:
        process = self.sandbox.exec(*command)
        process.wait()
        returncode = process.returncode
        if returncode is None:
            raise RuntimeError("Sandbox process finished without a return code")

        return CommandResult(
            returncode=returncode,
            stdout=process.stdout.read(),
            stderr=process.stderr.read(),
        )
