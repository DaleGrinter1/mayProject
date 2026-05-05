from dataclasses import dataclass
from pathlib import Path

from mayproject.sandbox.images import get_image
from mayproject.sandbox.runner import ModalSandboxRunner
from mayproject.sandbox.types import CommandResult, RunnerFactory, SandboxSpec


@dataclass(frozen=True)
class PythonConfig:
    """Stores where Python code runs on the remote computer.

    Attributes:
        remote_script_path: Where the Python file is placed remotely.
        timeout: How long the remote computer may run.
        idle_timeout: How long the remote computer may sit unused.
    """

    remote_script_path: str = "/tmp/script.py"
    timeout: int = 600
    idle_timeout: int = 120


@dataclass(frozen=True)
class PythonPrimitive:
    """Runs Python code on a remote computer.

    Attributes:
        app_name: The Modal app name to use.
        config: The Python run settings.
        runner_factory: Builds the remote computer runner.
    """

    app_name: str = "my-app"
    config: PythonConfig = PythonConfig()
    runner_factory: RunnerFactory = ModalSandboxRunner

    def run_code(self, code: str, *args: str) -> CommandResult:
        """Runs a small piece of Python text.

        Args:
            code: The Python text to run.
            *args: Extra words passed to the Python code.

        Returns:
            What the remote command printed and how it finished.
        """

        spec = SandboxSpec(
            app_name=self.app_name,
            image=get_image("python"),
            timeout=self.config.timeout,
            idle_timeout=self.config.idle_timeout,
            tags={"primitive": "python"},
        )

        with self.runner_factory(spec) as runner:
            runner.write_text(code, self.config.remote_script_path)
            return runner.exec("python", self.config.remote_script_path, *args)

    def run_script(self, script_path: Path, *args: str) -> CommandResult:
        """Runs a local Python file on the remote computer.

        Args:
            script_path: The Python file on this computer.
            *args: Extra words passed to the Python file.

        Returns:
            What the remote command printed and how it finished.
        """

        spec = SandboxSpec(
            app_name=self.app_name,
            image=get_image("python"),
            timeout=self.config.timeout,
            idle_timeout=self.config.idle_timeout,
            tags={"primitive": "python"},
        )

        with self.runner_factory(spec) as runner:
            runner.copy_from_local(script_path, self.config.remote_script_path)
            return runner.exec("python", self.config.remote_script_path, *args)
