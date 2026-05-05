from collections.abc import Sequence
from dataclasses import dataclass

from mayproject.sandbox.images import get_image
from mayproject.sandbox.runner import ModalSandboxRunner
from mayproject.sandbox.types import CommandResult, RunnerFactory, SandboxSpec


@dataclass(frozen=True)
class ShellConfig:
    timeout: int = 600
    idle_timeout: int = 120


@dataclass(frozen=True)
class ShellPrimitive:
    app_name: str = "my-app"
    config: ShellConfig = ShellConfig()
    runner_factory: RunnerFactory = ModalSandboxRunner

    def run(
        self,
        command: Sequence[str],
        timeout: int | None = None,
        idle_timeout: int | None = None,
    ) -> CommandResult:
        if not command:
            raise ValueError("Shell command must contain at least one argument")

        spec = SandboxSpec(
            app_name=self.app_name,
            image=get_image("python"),
            timeout=timeout or self.config.timeout,
            idle_timeout=idle_timeout or self.config.idle_timeout,
            tags={"primitive": "shell"},
        )

        with self.runner_factory(spec) as runner:
            return runner.exec(*command)
