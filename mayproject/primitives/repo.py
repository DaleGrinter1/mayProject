from collections.abc import Sequence
from dataclasses import dataclass

from mayproject.sandbox.images import get_image
from mayproject.sandbox.runner import ModalSandboxRunner
from mayproject.sandbox.types import CommandResult, RunnerFactory, SandboxSpec


@dataclass(frozen=True)
class RepoConfig:
    """Stores where a repository is copied on the remote computer.

    Attributes:
        workdir: Where the repository is copied remotely.
        timeout: How long the remote computer may run.
        idle_timeout: How long the remote computer may sit unused.
    """

    workdir: str = "/tmp/repo"
    timeout: int = 900
    idle_timeout: int = 180


@dataclass(frozen=True)
class RepoPrimitive:
    """Runs a command inside a copied repository.

    Attributes:
        app_name: The Modal app name to use.
        config: The repository run settings.
        runner_factory: Builds the remote computer runner.
    """

    app_name: str = "my-app"
    config: RepoConfig = RepoConfig()
    runner_factory: RunnerFactory = ModalSandboxRunner

    def run_command(self, repo_url: str, command: Sequence[str]) -> CommandResult:
        """Copies a repository and runs one command inside it.

        Args:
            repo_url: The repository web address.
            command: The command to run inside the repository.

        Returns:
            What the remote command printed and how it finished.
        """

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
    """Keeps one command part safe for a shell script.

    Args:
        value: One command word.

    Returns:
        The safely quoted command word.
    """

    # Keep each command part safe when it is placed into a shell script.
    return "'" + value.replace("'", "'\"'\"'") + "'"
