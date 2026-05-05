from dataclasses import dataclass
from pathlib import Path

from mayproject.sandbox.images import get_image
from mayproject.sandbox.runner import ModalSandboxRunner
from mayproject.sandbox.types import CommandResult, RunnerFactory, SandboxSpec


@dataclass(frozen=True)
class PythonConfig:
    remote_script_path: str = "/tmp/script.py"
    timeout: int = 600
    idle_timeout: int = 120


@dataclass(frozen=True)
class PythonPrimitive:
    app_name: str = "my-app"
    config: PythonConfig = PythonConfig()
    runner_factory: RunnerFactory = ModalSandboxRunner

    def run_code(self, code: str, *args: str) -> CommandResult:
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

