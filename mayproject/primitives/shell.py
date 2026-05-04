from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from mayproject.sandbox.images import python_image
from mayproject.sandbox.runner import ModalSandboxRunner, SandboxSpec
from mayproject.sandbox.results import (
    DEFAULT_RUN_ROOT,
    Artifact,
    SandboxResult,
    create_sandbox_run,
)


@dataclass(frozen=True)
class ShellCommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    result: SandboxResult

    @property
    def run(self):
        return self.result.run

    @property
    def status(self) -> str:
        return self.result.status

    def to_dict(self):
        data = self.result.to_dict()
        data["command"] = list(self.command)
        data["returncode"] = self.returncode
        return data


@dataclass(frozen=True)
class ShellPrimitive:
    app_name: str = "my-app"
    run_root: Path = DEFAULT_RUN_ROOT

    def run(
        self,
        command: Sequence[str],
        timeout: int = 600,
        idle_timeout: int = 120,
    ) -> ShellCommandResult:
        if not command:
            raise ValueError("Shell command must contain at least one argument")

        command_tuple = tuple(command)
        run = create_sandbox_run(
            "shell-command",
            run_root=self.run_root,
            tags={"primitive": "shell"},
            metadata={
                "command": list(command_tuple),
                "timeout": timeout,
                "idle_timeout": idle_timeout,
            },
        )
        spec = SandboxSpec(
            app_name=self.app_name,
            image=python_image(),
            timeout=timeout,
            idle_timeout=idle_timeout,
            tags={"primitive": "shell"},
        )

        with ModalSandboxRunner(spec) as runner:
            command_result = runner.exec(*command_tuple)

        stdout_path = run.artifact_dir / "stdout.txt"
        stderr_path = run.artifact_dir / "stderr.txt"
        stdout_path.write_text(command_result.stdout, encoding="utf-8")
        stderr_path.write_text(command_result.stderr, encoding="utf-8")

        status = "succeeded" if command_result.returncode == 0 else "failed"
        completed_run = run.complete(status)
        result = SandboxResult(
            run=completed_run,
            status=status,
            output={
                "command": list(command_tuple),
                "returncode": command_result.returncode,
            },
            artifacts=(
                Artifact("stdout", "text", stdout_path, "text/plain"),
                Artifact("stderr", "text", stderr_path, "text/plain"),
            ),
            stdout=command_result.stdout,
            stderr=command_result.stderr,
            error=None
            if command_result.returncode == 0
            else f"Shell command failed with return code {command_result.returncode}",
        )
        result.write_json(run.artifact_dir / "result.json")
        result.run.write_json(run.artifact_dir / "metadata.json")
        return ShellCommandResult(
            command=command_tuple,
            returncode=command_result.returncode,
            stdout=command_result.stdout,
            stderr=command_result.stderr,
            result=result,
        )
