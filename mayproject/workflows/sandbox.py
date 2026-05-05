from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
import subprocess
from typing import Protocol

import modal

from mayproject.sandbox.images import get_image
from mayproject.sandbox.runner import ModalSandboxRunner
from mayproject.sandbox.types import (
    CommandResult,
    RunnerFactory,
    SandboxHandle,
    SandboxSpec,
    VolumeMount,
)


class SandboxConnector(Protocol):
    def from_name(self, app_name: str, name: str) -> modal.Sandbox: ...

    def from_id(self, sandbox_id: str) -> modal.Sandbox: ...

    def list(self, *, tags: dict[str, str]) -> object: ...


@dataclass(frozen=True)
class ManagedSandbox:
    """Controls one remote computer on Modal."""

    app_name: str = "my-app"
    runner_factory: RunnerFactory = ModalSandboxRunner
    connector: SandboxConnector = ModalSandboxRunner
    not_found_errors: tuple[type[Exception], ...] = (modal.exception.NotFoundError,)
    run_shell_command: Callable[[Sequence[str]], int] | None = None

    def create(
        self,
        name: str,
        image_name: str = "python",
        volume_mounts: Iterable[VolumeMount] = (),
        command: Sequence[str] = ("sleep", "300"),
        timeout: int = 600,
        idle_timeout: int | None = 120,
    ) -> SandboxHandle:
        """Starts a remote computer on Modal."""

        existing = self._find_by_name(name)
        if existing is not None:
            return existing

        spec = SandboxSpec(
            app_name=self.app_name,
            command=tuple(command),
            name=name,
            image=get_image(image_name),
            volumes=build_volume_map(volume_mounts),
            timeout=timeout,
            idle_timeout=idle_timeout,
            tags={"managed": "true", "name": name, "image": image_name},
            terminate_on_exit=False,
        )
        with self.runner_factory(spec) as runner:
            return runner.handle()

    def list(self) -> list[SandboxHandle]:
        """Shows the remote computers this project started."""

        sandboxes = self.connector.list(tags={"managed": "true"})
        if hasattr(sandboxes, "__aiter__"):
            return asyncio.run(self._list_async(sandboxes))
        return list_handles(sandboxes, self.app_name)

    def status(self, name: str | None = None, sandbox_id: str | None = None) -> SandboxHandle:
        """Shows whether the remote computer is still running."""

        sandbox = self._connect(name=name, sandbox_id=sandbox_id)
        try:
            return handle_from_sandbox(sandbox, self.app_name, name)
        finally:
            sandbox.detach()

    def exec(
        self,
        command: Sequence[str],
        name: str | None = None,
        sandbox_id: str | None = None,
    ) -> CommandResult:
        """Runs a command inside the remote computer."""

        if not command:
            raise ValueError("Sandbox command must contain at least one argument")

        sandbox = self._connect(name=name, sandbox_id=sandbox_id)
        try:
            process = sandbox.exec(*command)
            process.wait()
            returncode = process.returncode
            if returncode is None:
                raise RuntimeError("Sandbox process finished without a return code")
            return CommandResult(
                returncode=returncode,
                stdout=process.stdout.read(),
                stderr=process.stderr.read(),
            )
        finally:
            sandbox.detach()

    def terminate(self, name: str | None = None, sandbox_id: str | None = None) -> int | None:
        """Stops the remote computer."""

        sandbox = self._connect(name=name, sandbox_id=sandbox_id)
        try:
            return sandbox.terminate(wait=True)
        finally:
            sandbox.detach()

    def shell(self, name: str | None = None, sandbox_id: str | None = None) -> int:
        """Opens a shell inside the remote computer."""

        handle = self.status(name=name, sandbox_id=sandbox_id)
        command = ["modal", "shell", handle.object_id, "--pty"]
        if self.run_shell_command is not None:
            return self.run_shell_command(command)
        return subprocess.run(command, check=False).returncode

    def _find_by_name(self, name: str) -> SandboxHandle | None:
        try:
            return self.status(name=name)
        except self.not_found_errors:
            return None

    async def _list_async(self, sandboxes: object) -> list[SandboxHandle]:
        handles: list[SandboxHandle] = []
        async for sandbox in sandboxes:
            handles.append(handle_from_sandbox(sandbox, self.app_name))
            sandbox.detach()
        return handles

    def _connect(self, name: str | None, sandbox_id: str | None) -> modal.Sandbox:
        if sandbox_id:
            return self.connector.from_id(sandbox_id)
        if name:
            return self.connector.from_name(self.app_name, name)
        raise ValueError("Sandbox name or ID is required")


def parse_volume_mount(text: str) -> VolumeMount:
    """Turns a volume setting into a saved folder and mount path."""

    name, separator, mount_path = text.partition(":")
    if not name or not separator or not mount_path:
        raise ValueError("Volume must look like name:/absolute/path")
    if not mount_path.startswith("/"):
        raise ValueError("Volume mount path must be absolute")
    return VolumeMount(name=name, mount_path=mount_path)


def build_volume_map(
    volume_mounts: Iterable[VolumeMount],
) -> dict[str, modal.Volume | modal.CloudBucketMount]:
    """Prepares saved folders for Modal."""

    volumes: dict[str, modal.Volume | modal.CloudBucketMount] = {}
    for mount in volume_mounts:
        volumes[mount.mount_path] = modal.Volume.from_name(
            mount.name,
            create_if_missing=mount.create_if_missing,
        )
    return volumes


def list_handles(sandboxes: Iterable[modal.Sandbox], app_name: str) -> list[SandboxHandle]:
    """Returns the remote computers in a simple list."""

    handles: list[SandboxHandle] = []
    for sandbox in sandboxes:
        handles.append(handle_from_sandbox(sandbox, app_name))
        sandbox.detach()
    return handles


def handle_from_sandbox(
    sandbox: modal.Sandbox,
    app_name: str,
    name: str | None = None,
) -> SandboxHandle:
    """Returns the name and ID for a remote computer."""

    sandbox.hydrate()
    return SandboxHandle(
        object_id=sandbox.object_id,
        app_name=app_name,
        name=name,
        tags=sandbox.get_tags(),
        returncode=sandbox.poll(),
    )
