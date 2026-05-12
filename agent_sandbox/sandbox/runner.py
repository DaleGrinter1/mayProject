from pathlib import Path

import modal

from agent_sandbox.sandbox.types import CommandResult, SandboxHandle, SandboxSpec


class ModalSandboxRunner:
    """Starts and talks to a remote computer on Modal.

    Attributes:
        spec: The instructions for the remote computer.
    """

    def __init__(self, spec: SandboxSpec) -> None:
        # Save the instructions until the remote computer is started.
        self.spec = spec
        self._sandbox: modal.Sandbox | None = None

    def __enter__(self) -> "ModalSandboxRunner":
        # Starting the context starts the remote computer.
        app = modal.App.lookup(self.spec.app_name, create_if_missing=True)
        create_kwargs = {
            "app": app,
            "timeout": self.spec.timeout,
            "idle_timeout": self.spec.idle_timeout,
            "verbose": self.spec.verbose,
        }
        optional_kwargs = {
            "name": self.spec.name,
            "image": self.spec.image,
            "volumes": self.spec.volumes or None,
            "env": self.spec.env or None,
            "workdir": self.spec.workdir,
            "cpu": self.spec.cpu,
            "memory": self.spec.memory,
            "gpu": self.spec.gpu,
        }
        create_kwargs.update(
            {key: value for key, value in optional_kwargs.items() if value is not None}
        )

        self._sandbox = modal.Sandbox.create(
            *self.spec.command,
            **create_kwargs,
        )
        self._sandbox.hydrate()
        if self.spec.tags:
            self._sandbox.set_tags(self.spec.tags)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._sandbox is None:
            return

        # Leaving the context either stops or detaches from the remote computer.
        try:
            if self.spec.terminate_on_exit:
                self._sandbox.terminate()
        finally:
            self._sandbox.detach()
            self._sandbox = None

    @property
    def sandbox(self) -> modal.Sandbox:
        """Returns the remote computer while it is open.

        Returns:
            The active Modal sandbox.
        """

        if self._sandbox is None:
            raise RuntimeError("Sandbox runner must be used as a context manager")
        return self._sandbox

    @classmethod
    def from_name(cls, app_name: str, name: str) -> modal.Sandbox:
        """Connects this project to an existing remote computer.

        Args:
            app_name: The Modal app name.
            name: The friendly sandbox name.

        Returns:
            The matching Modal sandbox.
        """

        return modal.Sandbox.from_name(app_name, name)

    @classmethod
    def from_id(cls, sandbox_id: str) -> modal.Sandbox:
        """Connects this project to a remote computer by its ID.

        Args:
            sandbox_id: The Modal sandbox ID.

        Returns:
            The matching Modal sandbox.
        """

        return modal.Sandbox.from_id(sandbox_id)

    @classmethod
    def list(cls, *, tags: dict[str, str]) -> object:
        """Finds remote computers that match the labels.

        Args:
            tags: Labels to match.

        Returns:
            Matching Modal sandboxes.
        """

        return modal.Sandbox.list(tags=tags)

    def handle(self) -> SandboxHandle:
        """Returns the name and ID for the remote computer.

        Returns:
            The remote computer details.
        """

        return SandboxHandle(
            object_id=self.sandbox.object_id,
            app_name=self.spec.app_name,
            name=self.spec.name,
            tags=self.sandbox.get_tags(),
            returncode=self.sandbox.poll(),
        )

    def write_text(self, content: str, remote_path: str) -> None:
        """Writes text into a file on the remote computer.

        Args:
            content: The text to write.
            remote_path: Where to write it remotely.
        """

        self.sandbox.filesystem.write_text(content, remote_path)

    def copy_from_local(self, local_path: Path, remote_path: str) -> None:
        """Copies a local file to the remote computer.

        Args:
            local_path: The file on this computer.
            remote_path: Where to place it remotely.
        """

        self.sandbox.filesystem.copy_from_local(local_path, remote_path)

    def copy_to_local(self, remote_path: str, local_path: Path) -> None:
        """Copies a remote file back to this computer.

        Args:
            remote_path: The file on the remote computer.
            local_path: Where to save it on this computer.
        """

        self.sandbox.filesystem.copy_to_local(remote_path, local_path)

    def exec(self, *command: str) -> CommandResult:
        """Runs one command on the remote computer.

        Args:
            *command: The command and its arguments.

        Returns:
            What the remote command printed and how it finished.
        """

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
