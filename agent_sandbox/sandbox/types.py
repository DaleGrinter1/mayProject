from collections.abc import Callable
from pathlib import Path
from typing import Literal
from typing import Protocol

import modal
from pydantic import BaseModel, ConfigDict, Field


ImageName = Literal["python", "browser", "dev"]


class FrozenSandboxModel(BaseModel):
    """Provides shared settings for sandbox data models."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)


class VolumeMount(FrozenSandboxModel):
    """Names a saved folder to attach to the remote computer.

    Attributes:
        name: The Modal Volume name.
        mount_path: Where the volume appears on the remote computer.
        create_if_missing: Whether to create the volume if it is missing.
    """

    name: str
    mount_path: str
    create_if_missing: bool = True


class SandboxHandle(FrozenSandboxModel):
    """Describes a remote computer that Modal is running.

    Attributes:
        object_id: The Modal ID for the remote computer.
        app_name: The Modal app name.
        name: The friendly sandbox name, if known.
        tags: Labels saved on the sandbox.
        returncode: The final code if the sandbox has stopped.
    """

    object_id: str
    app_name: str
    name: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    returncode: int | None = None


class SandboxSpec(FrozenSandboxModel):
    """Describes the remote computer this project should start.

    Attributes:
        app_name: The Modal app name.
        command: The command that keeps the sandbox alive.
        name: The friendly sandbox name.
        image: The Modal image to use.
        volumes: Saved folders to attach by remote path.
        env: Environment values to set remotely.
        workdir: The remote working folder.
        cpu: The requested CPU setting.
        memory: The requested memory setting.
        gpu: The requested GPU setting.
        timeout: How long the sandbox may run.
        idle_timeout: How long the sandbox may sit unused.
        verbose: Whether Modal should print extra details.
        tags: Labels to save on the sandbox.
        terminate_on_exit: Whether to stop the sandbox when leaving the runner.
    """

    app_name: str = "my-app"
    command: tuple[str, ...] = ("sleep", "300")
    name: str | None = None
    image: object | None = None
    volumes: dict[str, object] = Field(default_factory=dict)
    env: dict[str, str | None] = Field(default_factory=dict)
    workdir: str | None = None
    cpu: float | tuple[float, float] | None = None
    memory: int | tuple[int, int] | None = None
    gpu: str | None = None
    timeout: int = 600
    idle_timeout: int | None = 120
    verbose: bool = True
    tags: dict[str, str] = Field(default_factory=dict)
    terminate_on_exit: bool = True


class CommandResult(FrozenSandboxModel):
    """Holds what a remote command printed and how it finished.

    Attributes:
        returncode: The command's finish code.
        stdout: Text printed as normal output.
        stderr: Text printed as error output.
    """

    returncode: int
    stdout: str
    stderr: str


class SandboxRunner(Protocol):
    """Describes something that can control a remote computer."""

    # These methods let callers use the runner with `with ...`.
    def __enter__(self) -> "SandboxRunner": ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

    def write_text(self, content: str, remote_path: str) -> None:
        """Writes text into a remote file.

        Args:
            content: The text to write.
            remote_path: Where to write it remotely.
        """
        ...

    def copy_from_local(self, local_path: Path, remote_path: str) -> None:
        """Copies a local file to the remote computer.

        Args:
            local_path: The file on this computer.
            remote_path: Where to place it remotely.
        """
        ...

    def copy_to_local(self, remote_path: str, local_path: Path) -> None:
        """Copies a remote file back to this computer.

        Args:
            remote_path: The file on the remote computer.
            local_path: Where to save it on this computer.
        """
        ...

    def exec(self, *command: str) -> CommandResult:
        """Runs a command on the remote computer.

        Args:
            *command: The command and its arguments.

        Returns:
            What the remote command printed and how it finished.
        """
        ...

    def handle(self) -> SandboxHandle:
        """Returns the remote computer's name and ID.

        Returns:
            The remote computer details.
        """
        ...


RunnerFactory = Callable[[SandboxSpec], SandboxRunner]
