from collections.abc import Sequence
from dataclasses import dataclass

from mayproject.sandbox.images import get_image
from mayproject.sandbox.runner import ModalSandboxRunner
from mayproject.sandbox.types import CommandResult, RunnerFactory, SandboxSpec


@dataclass(frozen=True)
class RepoConfig:
    workdir: str = "/tmp/repo"
    timeout: int = 900
    idle_timeout: int = 180


@dataclass(frozen=True)
class RepoPrimitive:
    app_name: str = "my-app"
    config: RepoConfig = RepoConfig()
    runner_factory: RunnerFactory = ModalSandboxRunner

    def run_command(self, repo_url: str, command: Sequence[str]) -> CommandResult:
        if not repo_url:
            raise ValueError("Repository URL is required")
        if not command:
            raise ValueError("Repository command must contain at least one argument")

        spec = SandboxSpec(
            app_name=self.app_name,
            image=get_image("python"),
            timeout=self.config.timeout,
            idle_timeout=self.config.idle_timeout,
            tags={"primitive": "repo"},
        )

        command_text = " ".join(_shell_quote(part) for part in command)
        script = (
            "set -e\n"
            f"git clone --depth 1 {_shell_quote(repo_url)} {_shell_quote(self.config.workdir)}\n"
            f"cd {_shell_quote(self.config.workdir)}\n"
            f"{command_text}\n"
        )

        with self.runner_factory(spec) as runner:
            runner.write_text(script, "/tmp/run_repo_command.sh")
            return runner.exec("sh", "/tmp/run_repo_command.sh")


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"

