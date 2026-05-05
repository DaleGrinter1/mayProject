from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from typing import Protocol

import modal


ImageName = Literal["python", "browser"]


@dataclass(frozen=True)
class VolumeMount:
    """Names a saved folder to attach to the remote computer."""

    name: str
    mount_path: str
    create_if_missing: bool = True


@dataclass(frozen=True)
class SandboxHandle:
    """Describes a remote computer that Modal is running."""

    object_id: str
    app_name: str
    name: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    returncode: int | None = None


@dataclass(frozen=True)
class SandboxSpec:
    """Describes the remote computer this project should start."""

    app_name: str = "my-app"
    command: tuple[str, ...] = ("sleep", "300")
    name: str | None = None
    image: modal.Image | None = None
    volumes: dict[str, modal.Volume | modal.CloudBucketMount] = field(default_factory=dict)
    env: dict[str, str | None] = field(default_factory=dict)
    workdir: str | None = None
    cpu: float | tuple[float, float] | None = None
    memory: int | tuple[int, int] | None = None
    gpu: str | None = None
    timeout: int = 600
    idle_timeout: int | None = 120
    verbose: bool = True
    tags: dict[str, str] = field(default_factory=dict)
    terminate_on_exit: bool = True


@dataclass(frozen=True)
class CommandResult:
    """Holds what a remote command printed and how it finished."""

    returncode: int
    stdout: str
    stderr: str


class SandboxRunner(Protocol):
    def __enter__(self) -> "SandboxRunner": ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

    def write_text(self, content: str, remote_path: str) -> None: ...

    def copy_from_local(self, local_path: Path, remote_path: str) -> None: ...

    def copy_to_local(self, remote_path: str, local_path: Path) -> None: ...

    def exec(self, *command: str) -> CommandResult: ...

    def handle(self) -> SandboxHandle: ...


RunnerFactory = Callable[[SandboxSpec], SandboxRunner]
