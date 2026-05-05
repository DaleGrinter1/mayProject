from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Protocol

import modal

from mayproject.primitives.browser import SCREENSHOT_SCRIPT_PATH
from mayproject.sandbox.images import get_image
from mayproject.sandbox.runner import ModalSandboxRunner
from mayproject.sandbox.types import (
    CommandResult,
    RunnerFactory,
    SandboxHandle,
    SandboxSpec,
    VolumeMount,
)
from mayproject.workflows.screenshot import ScreenshotResult, screenshot_path


REMOTE_SCREENSHOT_SCRIPT_PATH = "/tmp/screenshot.py"
REMOTE_SCREENSHOT_IMAGE_PATH = "/tmp/screenshot.png"
REMOTE_SCREENSHOT_TEXT_PATH = "/tmp/observation.txt"


class SandboxConnector(Protocol):
    """Describes how to find remote computers on Modal."""

    def from_name(self, app_name: str, name: str) -> modal.Sandbox:
        """Finds a remote computer by name.

        Args:
            app_name: The Modal app name.
            name: The friendly sandbox name.

        Returns:
            The matching Modal sandbox.
        """
        ...

    def from_id(self, sandbox_id: str) -> modal.Sandbox:
        """Finds a remote computer by ID.

        Args:
            sandbox_id: The Modal sandbox ID.

        Returns:
            The matching Modal sandbox.
        """
        ...

    def list(self, *, tags: dict[str, str]) -> object:
        """Finds remote computers with matching labels.

        Args:
            tags: Labels to match.

        Returns:
            Matching Modal sandboxes.
        """
        ...


@dataclass(frozen=True)
class ManagedSandbox:
    """Controls one remote computer on Modal.

    Attributes:
        app_name: The Modal app name to use.
        runner_factory: Builds a new remote computer runner.
        connector: Finds existing remote computers.
        not_found_errors: Errors treated as missing sandboxes.
        run_shell_command: Optional shell command runner for tests.
    """

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
        """Starts a remote computer on Modal.

        Args:
            name: The friendly sandbox name.
            image_name: The image name to use.
            volume_mounts: Saved folders to attach.
            command: The command that keeps the sandbox alive.
            timeout: How long the sandbox may run.
            idle_timeout: How long the sandbox may sit unused.

        Returns:
            The remote computer details.
        """

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
        """Shows the remote computers this project started.

        Returns:
            Remote computers with this project's managed label.
        """

        sandboxes = self.connector.list(tags={"managed": "true"})
        if hasattr(sandboxes, "__aiter__"):
            return asyncio.run(self._list_async(sandboxes))
        return list_handles(sandboxes, self.app_name)

    def status(self, name: str | None = None, sandbox_id: str | None = None) -> SandboxHandle:
        """Shows whether the remote computer is still running.

        Args:
            name: The friendly sandbox name.
            sandbox_id: The Modal sandbox ID.

        Returns:
            The remote computer details.
        """

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
        """Runs a command inside the remote computer.

        Args:
            command: The command and its arguments.
            name: The friendly sandbox name.
            sandbox_id: The Modal sandbox ID.

        Returns:
            What the remote command printed and how it finished.
        """

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

    def copy_to(
        self,
        local_path: Path,
        remote_path: str,
        name: str | None = None,
        sandbox_id: str | None = None,
    ) -> None:
        """Copies a local file into the remote computer.

        Args:
            local_path: The file on this computer.
            remote_path: Where to put the file on the remote computer.
            name: The friendly sandbox name.
            sandbox_id: The Modal sandbox ID.
        """

        sandbox = self._connect(name=name, sandbox_id=sandbox_id)
        try:
            sandbox.filesystem.copy_from_local(local_path, remote_path)
        finally:
            sandbox.detach()

    def copy_from(
        self,
        remote_path: str,
        local_path: Path,
        name: str | None = None,
        sandbox_id: str | None = None,
    ) -> None:
        """Copies a remote file back to this computer.

        Args:
            remote_path: The file on the remote computer.
            local_path: Where to save the file on this computer.
            name: The friendly sandbox name.
            sandbox_id: The Modal sandbox ID.
        """

        sandbox = self._connect(name=name, sandbox_id=sandbox_id)
        try:
            sandbox.filesystem.copy_to_local(remote_path, local_path)
        finally:
            sandbox.detach()

    def screenshot(
        self,
        url: str,
        output_dir: Path = Path("screenshots"),
        name: str | None = None,
        sandbox_id: str | None = None,
    ) -> ScreenshotResult:
        """Takes a screenshot using an existing remote computer.

        Args:
            url: The web page to capture.
            output_dir: The folder for output files.
            name: The friendly sandbox name.
            sandbox_id: The Modal sandbox ID.

        Returns:
            The saved screenshot and notes paths.
        """

        image_path = screenshot_path(url, output_dir)
        text_path = image_path.with_suffix(".txt")
        sandbox = self._connect(name=name, sandbox_id=sandbox_id)
        try:
            sandbox.filesystem.copy_from_local(
                SCREENSHOT_SCRIPT_PATH,
                REMOTE_SCREENSHOT_SCRIPT_PATH,
            )
            process = sandbox.exec(
                "python",
                REMOTE_SCREENSHOT_SCRIPT_PATH,
                url,
                REMOTE_SCREENSHOT_IMAGE_PATH,
                REMOTE_SCREENSHOT_TEXT_PATH,
            )
            process.wait()
            returncode = process.returncode
            if returncode is None:
                raise RuntimeError("Sandbox process finished without a return code")

            stdout = process.stdout.read()
            stderr = process.stderr.read()
            if returncode != 0:
                detail = stderr or stdout
                raise RuntimeError(f"Screenshot failed in sandbox:\n{detail}")

            sandbox.filesystem.copy_to_local(REMOTE_SCREENSHOT_IMAGE_PATH, image_path)
            sandbox.filesystem.copy_to_local(REMOTE_SCREENSHOT_TEXT_PATH, text_path)
            return ScreenshotResult(url=url, image_path=image_path, text_path=text_path)
        finally:
            sandbox.detach()

    def terminate(self, name: str | None = None, sandbox_id: str | None = None) -> int | None:
        """Stops the remote computer.

        Args:
            name: The friendly sandbox name.
            sandbox_id: The Modal sandbox ID.

        Returns:
            The remote computer's final code, if Modal reports one.
        """

        sandbox = self._connect(name=name, sandbox_id=sandbox_id)
        try:
            return sandbox.terminate(wait=True)
        finally:
            sandbox.detach()

    def terminate_all(self) -> list[SandboxHandle]:
        """Stops every remote computer this project started.

        Returns:
            The remote computers that were asked to stop.
        """

        handles = self.list()
        for handle in handles:
            self.terminate(sandbox_id=handle.object_id)
        return handles

    def shell(self, name: str | None = None, sandbox_id: str | None = None) -> int:
        """Opens a shell inside the remote computer.

        Args:
            name: The friendly sandbox name.
            sandbox_id: The Modal sandbox ID.

        Returns:
            The shell command's finish code.
        """

        handle = self.status(name=name, sandbox_id=sandbox_id)
        command = ["modal", "shell", handle.object_id, "--pty"]
        if self.run_shell_command is not None:
            return self.run_shell_command(command)
        return subprocess.run(command, check=False).returncode

    def _find_by_name(self, name: str) -> SandboxHandle | None:
        """Finds a running remote computer by name.

        Args:
            name: The friendly sandbox name.

        Returns:
            The remote computer details, or None when it is missing.
        """

        # Reuse the remote computer if it is already running.
        try:
            return self.status(name=name)
        except self.not_found_errors:
            return None

    async def _list_async(self, sandboxes: object) -> list[SandboxHandle]:
        """Reads remote computers from an async Modal list.

        Args:
            sandboxes: Remote computers from Modal.

        Returns:
            The remote computer details.
        """

        # Some Modal versions return remote computers through an async list.
        handles: list[SandboxHandle] = []
        async for sandbox in sandboxes:
            handles.append(handle_from_sandbox(sandbox, self.app_name))
            sandbox.detach()
        return handles

    def _connect(self, name: str | None, sandbox_id: str | None) -> modal.Sandbox:
        """Connects to one remote computer.

        Args:
            name: The friendly sandbox name.
            sandbox_id: The Modal sandbox ID.

        Returns:
            The matching Modal sandbox.
        """

        # Prefer an exact ID when one is provided.
        if sandbox_id:
            return self.connector.from_id(sandbox_id)
        # Names are easier for people to remember than IDs.
        if name:
            return self.connector.from_name(self.app_name, name)
        raise ValueError("Sandbox name or ID is required")


def parse_volume_mount(text: str) -> VolumeMount:
    """Turns a volume setting into a saved folder and mount path.

    Args:
        text: Text like `volume-name:/remote/path`.

    Returns:
        The parsed volume mount.
    """

    name, separator, mount_path = text.partition(":")
    if not name or not separator or not mount_path:
        raise ValueError("Volume must look like name:/absolute/path")
    if not mount_path.startswith("/"):
        raise ValueError("Volume mount path must be absolute")
    return VolumeMount(name=name, mount_path=mount_path)


def build_volume_map(
    volume_mounts: Iterable[VolumeMount],
) -> dict[str, modal.Volume | modal.CloudBucketMount]:
    """Prepares saved folders for Modal.

    Args:
        volume_mounts: The saved folders to attach.

    Returns:
        Modal volumes keyed by remote path.
    """

    volumes: dict[str, modal.Volume | modal.CloudBucketMount] = {}
    for mount in volume_mounts:
        volumes[mount.mount_path] = modal.Volume.from_name(
            mount.name,
            create_if_missing=mount.create_if_missing,
        )
    return volumes


def list_handles(sandboxes: Iterable[modal.Sandbox], app_name: str) -> list[SandboxHandle]:
    """Returns the remote computers in a simple list.

    Args:
        sandboxes: Modal sandboxes to describe.
        app_name: The Modal app name.

    Returns:
        The remote computer details.
    """

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
    """Returns the name and ID for a remote computer.

    Args:
        sandbox: The Modal sandbox to describe.
        app_name: The Modal app name.
        name: The friendly sandbox name, if known.

    Returns:
        The remote computer details.
    """

    sandbox.hydrate()
    return SandboxHandle(
        object_id=sandbox.object_id,
        app_name=app_name,
        name=name,
        tags=sandbox.get_tags(),
        returncode=sandbox.poll(),
    )
