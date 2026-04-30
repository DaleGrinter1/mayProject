from collections.abc import Sequence
from dataclasses import dataclass

from mayproject.sandbox.images import python_image
from mayproject.sandbox.runner import CommandResult, ModalSandboxRunner, SandboxSpec


@dataclass(frozen=True)
class ShellPrimitive:
    app_name: str = "my-app"

    def run(
        self,
        command: Sequence[str],
        timeout: int = 600,
        idle_timeout: int = 120,
    ) -> CommandResult:
        if not command:
            raise ValueError("Shell command must contain at least one argument")

        spec = SandboxSpec(
            app_name=self.app_name,
            image=python_image(),
            timeout=timeout,
            idle_timeout=idle_timeout,
            tags={"primitive": "shell"},
        )

        with ModalSandboxRunner(spec) as runner:
            return runner.exec(*command)
