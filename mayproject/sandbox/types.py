from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from typing import Protocol

import modal


ImageName = Literal["python", "browser"]


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


class SandboxRunner(Protocol):
    def __enter__(self) -> "SandboxRunner": ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

    def write_text(self, content: str, remote_path: str) -> None: ...

    def copy_from_local(self, local_path: Path, remote_path: str) -> None: ...

    def copy_to_local(self, remote_path: str, local_path: Path) -> None: ...

    def exec(self, *command: str) -> CommandResult: ...


RunnerFactory = Callable[[SandboxSpec], SandboxRunner]
