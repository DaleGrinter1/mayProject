from pathlib import Path
import json

import pytest

from agent_sandbox.cli import sandbox as sandbox_cli
from agent_sandbox.cli.sandbox import (
    clear_terminal,
    friendly_error,
    main,
    positive_interval,
    watch_handles,
)
from agent_sandbox.sandbox.fake import FakeSandboxRunner
from agent_sandbox.sandbox.types import CommandResult, SandboxSpec
from agent_sandbox.workflows import sandbox as sandbox_workflow
from agent_sandbox.workflows.sandbox import ManagedSandbox, parse_volume_mount


class MissingSandbox(Exception):
    """Stands in for Modal's missing sandbox error in tests."""

    pass


class RunnerRecorder:
    """Keeps fake runners so tests can inspect how they were used."""

    def __init__(self) -> None:
        """Creates an empty runner history."""

        self.runners: list[FakeSandboxRunner] = []

    def factory(self, spec: SandboxSpec) -> FakeSandboxRunner:
        """Builds and records one fake sandbox runner.

        Args:
            spec: The remote computer settings passed by the workflow.

        Returns:
            A fake runner for the test to inspect later.
        """

        runner = FakeSandboxRunner(spec)
        self.runners.append(runner)
        return runner


class FakeStream:
    """Acts like a Modal stream that returns fixed text."""

    def __init__(self, text: str) -> None:
        """Stores the text the stream should return.

        Args:
            text: The stream contents.
        """

        self.text = text

    def read(self) -> str:
        """Returns the stored stream contents.

        Returns:
            The stream text.
        """

        return self.text


class FakeProcess:
    """Acts like a Modal process result."""

    def __init__(self, result: CommandResult) -> None:
        """Builds a fake process from a command result.

        Args:
            result: The command result to expose through process fields.
        """

        self.returncode: int | None = result.returncode
        self.stdout = FakeStream(result.stdout)
        self.stderr = FakeStream(result.stderr)

    def wait(self) -> None:
        """Pretends to wait for the remote process to finish."""

        return None


class FakeFilesystem:
    """Acts like a Modal sandbox filesystem in tests."""

    def __init__(self) -> None:
        """Creates empty copy histories."""

        self.copied_from_local: list[tuple[Path, str]] = []
        self.copied_to_local: list[tuple[str, Path]] = []

    def copy_from_local(self, local_path: Path, remote_path: str) -> None:
        """Records a local-to-remote copy.

        Args:
            local_path: The local file path.
            remote_path: The remote file path.
        """

        self.copied_from_local.append((local_path, remote_path))

    def copy_to_local(self, remote_path: str, local_path: Path) -> None:
        """Records a remote-to-local copy.

        Args:
            remote_path: The remote file path.
            local_path: The local file path.
        """

        self.copied_to_local.append((remote_path, local_path))


class FakeRemoteSandbox:
    """Acts like a Modal sandbox for managed sandbox tests."""

    def __init__(
        self,
        object_id: str = "sb-123",
        result: CommandResult | None = None,
        tags: dict[str, str] | None = None,
        returncode: int | None = None,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        """Creates a fake remote computer.

        Args:
            object_id: The fake Modal sandbox ID.
            result: The command result to return from remote exec calls.
            tags: The fake labels attached to the sandbox.
            returncode: The fake sandbox finish code.
            stdout: The fake sandbox root process stdout.
            stderr: The fake sandbox root process stderr.
        """

        self.object_id = object_id
        self.result = result or CommandResult(returncode=0, stdout="", stderr="")
        self.tags = tags or {"managed": "true"}
        self.returncode = returncode
        self.stdout = FakeStream(stdout)
        self.stderr = FakeStream(stderr)
        self.filesystem = FakeFilesystem()
        self.commands: list[tuple[str, ...]] = []
        self.detached = False
        self.terminated = False

    def hydrate(self) -> None:
        """Pretends to load the remote computer details."""

        return None

    def get_tags(self) -> dict[str, str]:
        """Returns the fake labels attached to the sandbox.

        Returns:
            The sandbox tags.
        """

        return self.tags

    def poll(self) -> int | None:
        """Returns the fake sandbox state.

        Returns:
            The fake sandbox return code.
        """

        return self.returncode

    def exec(self, *command: str) -> FakeProcess:
        """Records a command and returns the fake process result.

        Args:
            *command: The command words sent to the remote computer.

        Returns:
            A fake process for the command.
        """

        self.commands.append(command)
        return FakeProcess(self.result)

    def terminate(self, wait: bool = False) -> int | None:
        """Marks the fake sandbox as terminated.

        Args:
            wait: Whether the caller asked to wait for termination.

        Returns:
            Zero to mimic a successful stop.
        """

        self.terminated = wait
        return 0

    def detach(self) -> None:
        """Marks the fake sandbox as detached."""

        self.detached = True


class FakeConnector:
    """Finds fake remote computers for managed sandbox tests."""

    def __init__(
        self,
        sandbox: FakeRemoteSandbox | None = None,
        sandboxes: list[FakeRemoteSandbox] | None = None,
    ) -> None:
        """Stores the fake sandbox or sandbox list to return.

        Args:
            sandbox: The sandbox returned by name or ID lookups.
            sandboxes: The sandboxes returned by list calls.
        """

        self.sandbox = sandbox
        self.sandboxes = sandboxes or []
        self.list_tags: dict[str, str] | None = None

    def from_name(self, app_name: str, name: str) -> FakeRemoteSandbox:
        """Finds a fake sandbox by name.

        Args:
            app_name: The Modal app name.
            name: The friendly sandbox name.

        Returns:
            The configured fake sandbox.
        """

        if self.sandbox is None:
            raise MissingSandbox(name)
        return self.sandbox

    def from_id(self, sandbox_id: str) -> FakeRemoteSandbox:
        """Finds a fake sandbox by ID.

        Args:
            sandbox_id: The Modal sandbox ID.

        Returns:
            The configured fake sandbox.
        """

        if self.sandbox is None:
            raise MissingSandbox(sandbox_id)
        return self.sandbox

    async def list(self, *, tags: dict[str, str]):
        """Lists fake sandboxes matching tags.

        Args:
            tags: The labels requested by the workflow.
        """

        self.list_tags = tags
        for sandbox in self.sandboxes:
            yield sandbox


class SyncListConnector(FakeConnector):
    """Returns fake sandboxes through a normal iterator."""

    def list(self, *, tags: dict[str, str]):
        """Lists fake sandboxes without async iteration.

        Args:
            tags: The labels requested by the workflow.
        """

        self.list_tags = tags
        yield from self.sandboxes


class TerminateAllConnector(FakeConnector):
    """Finds listed fake sandboxes again by ID for termination tests."""

    def __init__(self, sandboxes: list[FakeRemoteSandbox]) -> None:
        """Builds a connector indexed by fake sandbox ID.

        Args:
            sandboxes: The fake sandboxes available to terminate.
        """

        super().__init__(sandboxes=sandboxes)
        self.by_id = {sandbox.object_id: sandbox for sandbox in sandboxes}

    def from_id(self, sandbox_id: str) -> FakeRemoteSandbox:
        """Finds a listed fake sandbox by ID.

        Args:
            sandbox_id: The fake Modal sandbox ID.

        Returns:
            The matching fake sandbox.
        """

        return self.by_id[sandbox_id]


def test_parse_volume_mount_accepts_name_and_absolute_path() -> None:
    mount = parse_volume_mount("data:/workspace/data")

    assert mount.name == "data"
    assert mount.mount_path == "/workspace/data"
    assert mount.create_if_missing


@pytest.mark.parametrize("text", ["data", "data:", ":/workspace/data"])
def test_parse_volume_mount_rejects_missing_parts(text: str) -> None:
    with pytest.raises(ValueError, match="name:/absolute/path"):
        parse_volume_mount(text)


def test_parse_volume_mount_rejects_relative_mount_path() -> None:
    with pytest.raises(ValueError, match="absolute"):
        parse_volume_mount("data:workspace/data")


def test_build_volume_map_looks_up_modal_volumes(monkeypatch) -> None:
    looked_up: list[tuple[str, bool]] = []

    def from_name(name: str, create_if_missing: bool = False) -> object:
        looked_up.append((name, create_if_missing))
        return object()

    monkeypatch.setattr(sandbox_workflow.modal.Volume, "from_name", from_name)

    volumes = sandbox_workflow.build_volume_map(
        [parse_volume_mount("data:/workspace/data")]
    )

    assert list(volumes) == ["/workspace/data"]
    assert looked_up == [("data", True)]


def test_create_passes_named_sandbox_image_and_volumes(monkeypatch) -> None:
    recorder = RunnerRecorder()
    volume = object()
    monkeypatch.setattr(sandbox_workflow, "get_image", lambda name: f"{name}-image")
    monkeypatch.setattr(
        sandbox_workflow,
        "build_volume_map",
        lambda mounts: {"/workspace/data": volume},
    )
    manager = ManagedSandbox(
        app_name="test-app",
        runner_factory=recorder.factory,
        connector=FakeConnector(),
        not_found_errors=(MissingSandbox,),
    )

    handle = manager.create(
        name="devbox",
        image_name="python",
        volume_mounts=[parse_volume_mount("data:/workspace/data")],
    )

    runner = recorder.runners[0]
    assert handle.object_id == "fake-devbox"
    assert runner.closed
    assert not runner.terminated
    assert runner.spec.app_name == "test-app"
    assert runner.spec.name == "devbox"
    assert runner.spec.image == "python-image"
    assert runner.spec.volumes == {"/workspace/data": volume}
    assert runner.spec.tags == {"managed": "true", "name": "devbox", "image": "python"}


def test_create_returns_existing_named_sandbox() -> None:
    remote = FakeRemoteSandbox(object_id="sb-existing")
    manager = ManagedSandbox(
        app_name="test-app",
        runner_factory=RunnerRecorder().factory,
        connector=FakeConnector(remote),
        not_found_errors=(MissingSandbox,),
    )

    handle = manager.create(name="devbox")

    assert handle.object_id == "sb-existing"
    assert handle.name == "devbox"
    assert remote.detached


def test_list_returns_managed_sandboxes() -> None:
    pybox = FakeRemoteSandbox(
        object_id="sb-py",
        tags={"managed": "true", "name": "pybox", "image": "python"},
    )
    browserbox = FakeRemoteSandbox(
        object_id="sb-browser",
        tags={"managed": "true", "name": "browserbox", "image": "browser"},
    )
    connector = FakeConnector(sandboxes=[pybox, browserbox])
    manager = ManagedSandbox(connector=connector)

    handles = manager.list()

    assert connector.list_tags == {"managed": "true"}
    assert [handle.object_id for handle in handles] == ["sb-py", "sb-browser"]
    assert handles[0].tags["image"] == "python"
    assert pybox.detached
    assert browserbox.detached


def test_list_accepts_sync_sandbox_iterators() -> None:
    pybox = FakeRemoteSandbox(
        object_id="sb-py",
        tags={"managed": "true", "name": "pybox", "image": "python"},
    )
    connector = SyncListConnector(sandboxes=[pybox])
    manager = ManagedSandbox(connector=connector)

    handles = manager.list()

    assert connector.list_tags == {"managed": "true"}
    assert [handle.object_id for handle in handles] == ["sb-py"]
    assert pybox.detached


def test_exec_rejects_empty_command() -> None:
    manager = ManagedSandbox(connector=FakeConnector(FakeRemoteSandbox()))

    with pytest.raises(ValueError, match="at least one argument"):
        manager.exec([], name="devbox")


def test_exec_runs_command_and_detaches() -> None:
    remote = FakeRemoteSandbox(
        result=CommandResult(returncode=7, stdout="out", stderr="err")
    )
    manager = ManagedSandbox(connector=FakeConnector(remote))

    result = manager.exec(["python", "--version"], name="devbox")

    assert result == CommandResult(returncode=7, stdout="out", stderr="err")
    assert remote.commands == [("python", "--version")]
    assert remote.detached


def test_copy_to_copies_local_file_and_detaches() -> None:
    remote = FakeRemoteSandbox()
    manager = ManagedSandbox(connector=FakeConnector(remote))

    manager.copy_to(Path("local.txt"), "/workspace/local.txt", name="devbox")

    assert remote.filesystem.copied_from_local == [
        (Path("local.txt"), "/workspace/local.txt")
    ]
    assert remote.detached


def test_copy_from_copies_remote_file_and_detaches() -> None:
    remote = FakeRemoteSandbox()
    manager = ManagedSandbox(connector=FakeConnector(remote))

    manager.copy_from("/workspace/result.txt", Path("result.txt"), sandbox_id="sb-123")

    assert remote.filesystem.copied_to_local == [
        ("/workspace/result.txt", Path("result.txt"))
    ]
    assert remote.detached


def test_screenshot_uses_existing_sandbox_and_copies_outputs(tmp_path, monkeypatch) -> None:
    remote = FakeRemoteSandbox()
    image_path = tmp_path / "example.png"
    monkeypatch.setattr(
        sandbox_workflow,
        "screenshot_path",
        lambda url, output_dir: image_path,
    )
    manager = ManagedSandbox(connector=FakeConnector(remote))

    result = manager.screenshot("https://example.com", name="devbox")

    assert result.url == "https://example.com"
    assert result.image_path == image_path
    assert result.text_path == tmp_path / "example.txt"
    assert remote.filesystem.copied_from_local[0][0].name == "screenshot_page.py"
    assert remote.filesystem.copied_from_local[0][1] == "/tmp/screenshot.py"
    assert remote.commands == [
        (
            "python",
            "/tmp/screenshot.py",
            "https://example.com",
            "/tmp/screenshot.png",
            "/tmp/observation.txt",
        )
    ]
    assert remote.filesystem.copied_to_local == [
        ("/tmp/screenshot.png", image_path),
        ("/tmp/observation.txt", tmp_path / "example.txt"),
    ]
    assert remote.detached


def test_shell_resolves_sandbox_and_runs_modal_shell() -> None:
    remote = FakeRemoteSandbox(object_id="sb-shell")
    commands: list[list[str]] = []
    manager = ManagedSandbox(
        connector=FakeConnector(remote),
        run_shell_command=lambda command: commands.append(list(command)) or 0,
    )

    result = manager.shell(name="devbox")

    assert result == 0
    assert commands == [["modal", "shell", "sb-shell", "--pty"]]
    assert remote.detached


def test_terminate_stops_and_detaches() -> None:
    remote = FakeRemoteSandbox()
    manager = ManagedSandbox(connector=FakeConnector(remote))

    result = manager.terminate(name="devbox")

    assert result == 0
    assert remote.terminated
    assert remote.detached


def test_logs_reads_stopped_sandbox_output_and_detaches() -> None:
    remote = FakeRemoteSandbox(returncode=4, stdout="out\n", stderr="err\n")
    manager = ManagedSandbox(connector=FakeConnector(remote))

    result = manager.logs(name="devbox")

    assert result == CommandResult(returncode=4, stdout="out\n", stderr="err\n")
    assert remote.detached


def test_logs_rejects_running_sandbox_and_detaches() -> None:
    remote = FakeRemoteSandbox(returncode=None)
    manager = ManagedSandbox(connector=FakeConnector(remote))

    with pytest.raises(ValueError, match="after the sandbox stops"):
        manager.logs(name="devbox")

    assert remote.detached


def test_terminate_all_stops_listed_sandboxes() -> None:
    pybox = FakeRemoteSandbox(object_id="sb-py")
    browserbox = FakeRemoteSandbox(object_id="sb-browser")
    connector = TerminateAllConnector([pybox, browserbox])
    manager = ManagedSandbox(connector=connector)

    handles = manager.terminate_all()

    assert [handle.object_id for handle in handles] == ["sb-py", "sb-browser"]
    assert pybox.terminated
    assert browserbox.terminated


def test_cli_list_prints_sandbox_rows(monkeypatch, capsys) -> None:
    handles = [
        sandbox_workflow.SandboxHandle(
            object_id="sb-py",
            app_name="my-app",
            tags={"name": "pybox", "image": "python"},
        ),
        sandbox_workflow.SandboxHandle(
            object_id="sb-browser",
            app_name="my-app",
            tags={"name": "browserbox", "image": "browser"},
        ),
    ]

    monkeypatch.setattr(sandbox_workflow.ManagedSandbox, "list", lambda self: handles)

    result = main(["list"])

    output = capsys.readouterr().out
    assert result == 0
    assert "| Name" in output
    assert "| Image" in output
    assert "| State" in output
    assert "| Sandbox ID" in output
    assert "pybox" in output
    assert "python" in output
    assert "browserbox" in output
    assert "browser" in output


def test_cli_list_prints_json_rows(monkeypatch, capsys) -> None:
    handles = [
        sandbox_workflow.SandboxHandle(
            object_id="sb-py",
            app_name="my-app",
            tags={"name": "pybox", "image": "python"},
        )
    ]

    monkeypatch.setattr(sandbox_workflow.ManagedSandbox, "list", lambda self: handles)

    result = main(["list", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload == [
        {
            "app_name": "my-app",
            "image": "python",
            "name": "pybox",
            "returncode": None,
            "sandbox_id": "sb-py",
            "state": "running",
            "tags": {"name": "pybox", "image": "python"},
        }
    ]


def test_cli_inspect_by_name_prints_sandbox_details(monkeypatch, capsys) -> None:
    calls: list[tuple[str | None, str | None]] = []

    class InspectManager:
        def __init__(self, app_name: str) -> None:
            self.app_name = app_name

        def status(
            self,
            name: str | None = None,
            sandbox_id: str | None = None,
        ) -> sandbox_workflow.SandboxHandle:
            calls.append((name, sandbox_id))
            return sandbox_workflow.SandboxHandle(
                object_id="sb-devbox",
                app_name=self.app_name,
                name=name,
                tags={
                    "managed": "true",
                    "name": "devbox",
                    "image": "dev",
                    "owner": "tests",
                },
            )

    monkeypatch.setattr(sandbox_cli, "ManagedSandbox", InspectManager)

    result = main(["inspect", "--name", "devbox"])

    output = capsys.readouterr().out
    assert result == 0
    assert calls == [("devbox", None)]
    assert "Name" in output
    assert "devbox" in output
    assert "Sandbox ID" in output
    assert "sb-devbox" in output
    assert "App name" in output
    assert "my-app" in output
    assert "Image" in output
    assert "dev" in output
    assert "State" in output
    assert "running" in output
    assert "Tags" in output
    assert "managed" in output
    assert "owner" in output
    assert "tests" in output


def test_cli_inspect_prints_json(monkeypatch, capsys) -> None:
    class InspectManager:
        def __init__(self, app_name: str) -> None:
            self.app_name = app_name

        def status(
            self,
            name: str | None = None,
            sandbox_id: str | None = None,
        ) -> sandbox_workflow.SandboxHandle:
            return sandbox_workflow.SandboxHandle(
                object_id="sb-devbox",
                app_name=self.app_name,
                name=name,
                tags={"managed": "true", "name": "devbox", "image": "dev"},
            )

    monkeypatch.setattr(sandbox_cli, "ManagedSandbox", InspectManager)

    result = main(["inspect", "--name", "devbox", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload["sandbox_id"] == "sb-devbox"
    assert payload["name"] == "devbox"
    assert payload["image"] == "dev"
    assert payload["state"] == "running"
    assert payload["tags"] == {"managed": "true", "name": "devbox", "image": "dev"}


def test_cli_inspect_by_id_prints_done_state(monkeypatch, capsys) -> None:
    calls: list[tuple[str | None, str | None]] = []

    class InspectManager:
        def __init__(self, app_name: str) -> None:
            self.app_name = app_name

        def status(
            self,
            name: str | None = None,
            sandbox_id: str | None = None,
        ) -> sandbox_workflow.SandboxHandle:
            calls.append((name, sandbox_id))
            return sandbox_workflow.SandboxHandle(
                object_id=sandbox_id or "sb-missing",
                app_name=self.app_name,
                tags={"managed": "true", "name": "devbox", "image": "python"},
                returncode=7,
            )

    monkeypatch.setattr(sandbox_cli, "ManagedSandbox", InspectManager)

    result = main(["inspect", "--id", "sb-123"])

    output = capsys.readouterr().out
    assert result == 0
    assert calls == [(None, "sb-123")]
    assert "devbox" in output
    assert "sb-123" in output
    assert "my-app" in output
    assert "python" in output
    assert "done:7" in output
    assert "managed" in output


def test_cli_status_prints_json(monkeypatch, capsys) -> None:
    class StatusManager:
        def __init__(self, app_name: str) -> None:
            self.app_name = app_name

        def status(
            self,
            name: str | None = None,
            sandbox_id: str | None = None,
        ) -> sandbox_workflow.SandboxHandle:
            return sandbox_workflow.SandboxHandle(
                object_id=sandbox_id or "sb-missing",
                app_name=self.app_name,
                tags={"name": "devbox", "image": "python"},
                returncode=3,
            )

    monkeypatch.setattr(sandbox_cli, "ManagedSandbox", StatusManager)

    result = main(["status", "--id", "sb-123", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload["sandbox_id"] == "sb-123"
    assert payload["state"] == "done:3"


def test_cli_copy_to_uses_name_and_prints_paths(monkeypatch, capsys) -> None:
    calls: list[tuple[Path, str, str | None, str | None]] = []

    class CopyManager:
        def __init__(self, app_name: str) -> None:
            self.app_name = app_name

        def copy_to(
            self,
            local_path: Path,
            remote_path: str,
            name: str | None = None,
            sandbox_id: str | None = None,
        ) -> None:
            calls.append((local_path, remote_path, name, sandbox_id))

    monkeypatch.setattr(sandbox_cli, "ManagedSandbox", CopyManager)

    result = main(["copy-to", "--name", "devbox", "local.txt", "/workspace/local.txt"])

    output = capsys.readouterr().out
    assert result == 0
    assert calls == [(Path("local.txt"), "/workspace/local.txt", "devbox", None)]
    assert "local.txt" in output
    assert "/workspace/local.txt" in output


def test_cli_put_alias_copies_to_sandbox(monkeypatch, capsys) -> None:
    calls: list[tuple[Path, str, str | None, str | None]] = []

    class CopyManager:
        def __init__(self, app_name: str) -> None:
            self.app_name = app_name

        def copy_to(
            self,
            local_path: Path,
            remote_path: str,
            name: str | None = None,
            sandbox_id: str | None = None,
        ) -> None:
            calls.append((local_path, remote_path, name, sandbox_id))

    monkeypatch.setattr(sandbox_cli, "ManagedSandbox", CopyManager)

    result = main(["put", "--name", "devbox", "local.txt", "/workspace/local.txt"])

    output = capsys.readouterr().out
    assert result == 0
    assert calls == [(Path("local.txt"), "/workspace/local.txt", "devbox", None)]
    assert "Copied local.txt to /workspace/local.txt" in output


def test_cli_copy_from_uses_id_and_prints_paths(monkeypatch, capsys) -> None:
    calls: list[tuple[str, Path, str | None, str | None]] = []

    class CopyManager:
        def __init__(self, app_name: str) -> None:
            self.app_name = app_name

        def copy_from(
            self,
            remote_path: str,
            local_path: Path,
            name: str | None = None,
            sandbox_id: str | None = None,
        ) -> None:
            calls.append((remote_path, local_path, name, sandbox_id))

    monkeypatch.setattr(sandbox_cli, "ManagedSandbox", CopyManager)

    result = main(
        ["copy-from", "--id", "sb-123", "/workspace/result.txt", "result.txt"]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert calls == [("/workspace/result.txt", Path("result.txt"), None, "sb-123")]
    assert "/workspace/result.txt" in output
    assert "result.txt" in output


def test_cli_get_alias_copies_from_sandbox(monkeypatch, capsys) -> None:
    calls: list[tuple[str, Path, str | None, str | None]] = []

    class CopyManager:
        def __init__(self, app_name: str) -> None:
            self.app_name = app_name

        def copy_from(
            self,
            remote_path: str,
            local_path: Path,
            name: str | None = None,
            sandbox_id: str | None = None,
        ) -> None:
            calls.append((remote_path, local_path, name, sandbox_id))

    monkeypatch.setattr(sandbox_cli, "ManagedSandbox", CopyManager)

    result = main(["get", "--id", "sb-123", "/workspace/result.txt", "result.txt"])

    output = capsys.readouterr().out
    assert result == 0
    assert calls == [("/workspace/result.txt", Path("result.txt"), None, "sb-123")]
    assert "Copied /workspace/result.txt to result.txt" in output


def test_cli_screenshot_uses_name_and_prints_saved_paths(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    calls: list[tuple[str, str | None, str | None]] = []
    image_path = tmp_path / "example.png"
    text_path = tmp_path / "example.txt"

    class ScreenshotManager:
        def __init__(self, app_name: str) -> None:
            self.app_name = app_name

        def screenshot(
            self,
            url: str,
            output_dir: Path = Path("artifacts/screenshots"),
            name: str | None = None,
            sandbox_id: str | None = None,
        ) -> sandbox_workflow.ScreenshotResult:
            calls.append((url, name, sandbox_id))
            return sandbox_workflow.ScreenshotResult(url, image_path, text_path)

    monkeypatch.setattr(sandbox_cli, "ManagedSandbox", ScreenshotManager)

    result = main(["screenshot", "--name", "devbox", "https://example.com"])

    output = capsys.readouterr().out
    assert result == 0
    assert calls == [("https://example.com", "devbox", None)]
    assert "Screenshot target: https://example.com" in output
    assert str(image_path.resolve()) in output
    assert str(text_path.resolve()) in output


def test_cli_screenshot_accepts_output_dir(monkeypatch, capsys) -> None:
    calls: list[tuple[str, Path, str | None, str | None]] = []

    class ScreenshotManager:
        def __init__(self, app_name: str) -> None:
            self.app_name = app_name

        def screenshot(
            self,
            url: str,
            output_dir: Path = Path("artifacts/screenshots"),
            name: str | None = None,
            sandbox_id: str | None = None,
        ) -> sandbox_workflow.ScreenshotResult:
            calls.append((url, output_dir, name, sandbox_id))
            return sandbox_workflow.ScreenshotResult(
                url,
                output_dir / "example.png",
                output_dir / "example.txt",
            )

    monkeypatch.setattr(sandbox_cli, "ManagedSandbox", ScreenshotManager)

    result = main(
        [
            "screenshot",
            "--name",
            "devbox",
            "--output-dir",
            "artifacts/custom-shots",
            "https://example.com",
        ]
    )

    assert result == 0
    assert calls == [
        (
            "https://example.com",
            Path("artifacts/custom-shots"),
            "devbox",
            None,
        )
    ]


def test_cli_screenshot_uses_id_and_resolves_search_terms(monkeypatch, capsys) -> None:
    calls: list[tuple[str, str | None, str | None]] = []

    class ScreenshotManager:
        def __init__(self, app_name: str) -> None:
            self.app_name = app_name

        def screenshot(
            self,
            url: str,
            output_dir: Path = Path("artifacts/screenshots"),
            name: str | None = None,
            sandbox_id: str | None = None,
        ) -> sandbox_workflow.ScreenshotResult:
            calls.append((url, name, sandbox_id))
            return sandbox_workflow.ScreenshotResult(
                url,
                Path("artifacts/screenshots/example.png"),
                Path("artifacts/screenshots/example.txt"),
            )

    monkeypatch.setattr(sandbox_cli, "ManagedSandbox", ScreenshotManager)
    monkeypatch.setattr(
        sandbox_cli,
        "first_search_result",
        lambda query: "https://example.com/search-result",
    )

    result = main(["screenshot", "--id", "sb-123", "example", "search"])

    output = capsys.readouterr().out
    assert result == 0
    assert calls == [("https://example.com/search-result", None, "sb-123")]
    assert "Screenshot target: https://example.com/search-result" in output


def test_cli_logs_prints_stdout_and_stderr(monkeypatch, capsys) -> None:
    calls: list[tuple[str | None, str | None]] = []

    class LogsManager:
        def __init__(self, app_name: str) -> None:
            self.app_name = app_name

        def logs(
            self,
            name: str | None = None,
            sandbox_id: str | None = None,
        ) -> CommandResult:
            calls.append((name, sandbox_id))
            return CommandResult(returncode=5, stdout="out\n", stderr="err\n")

    monkeypatch.setattr(sandbox_cli, "ManagedSandbox", LogsManager)

    result = main(["logs", "--id", "sb-123"])

    captured = capsys.readouterr()
    assert result == 5
    assert calls == [(None, "sb-123")]
    assert captured.out == "out\n"
    assert captured.err == "err\n"


def test_cli_doctor_prints_checks(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        sandbox_cli,
        "run_doctor",
        lambda: [
            sandbox_cli.DoctorCheck("Modal CLI", True, "Modal CLI found."),
            sandbox_cli.DoctorCheck("Images", True, "Available images: python, browser, dev."),
        ],
    )

    result = main(["doctor"])

    output = capsys.readouterr().out
    assert result == 0
    assert "Modal CLI" in output
    assert "Available images" in output


def test_cli_terminate_all_prints_stopped_sandboxes(monkeypatch, capsys) -> None:
    handles = [
        sandbox_workflow.SandboxHandle(
            object_id="sb-py",
            app_name="my-app",
            tags={"name": "pybox", "image": "python"},
        )
    ]
    monkeypatch.setattr(
        sandbox_workflow.ManagedSandbox,
        "terminate_all",
        lambda self: handles,
    )

    result = main(["terminate-all"])

    output = capsys.readouterr().out
    assert result == 0
    assert "pybox" in output
    assert "Terminated 1 managed sandbox" in output


def test_watch_handles_refreshes_until_keyboard_interrupt(capsys) -> None:
    class ListingManager:
        def __init__(self) -> None:
            self.calls = 0

        def list(self) -> list[object]:
            self.calls += 1
            return [
                sandbox_workflow.SandboxHandle(
                    object_id="sb-py",
                    app_name="my-app",
                    tags={"name": "pybox", "image": "python"},
                )
            ]

    manager = ListingManager()
    clears: list[str] = []

    def stop_after_one_sleep(interval: float) -> None:
        raise KeyboardInterrupt

    watch_handles(
        manager,
        interval=0.5,
        sleep_fn=stop_after_one_sleep,
        clear_screen=lambda: clears.append("clear"),
    )

    output = capsys.readouterr().out
    assert manager.calls == 1
    assert clears == ["clear"]
    assert "pybox" in output
    assert "Refreshing every 0.5s" in output
    assert "Stopped watching sandboxes." in output


def test_watch_handles_clears_after_fetching_list() -> None:
    events: list[str] = []

    class ListingManager:
        def list(self) -> list[object]:
            events.append("list")
            return []

    def stop_after_one_sleep(interval: float) -> None:
        events.append("sleep")
        raise KeyboardInterrupt

    watch_handles(
        ListingManager(),
        interval=1,
        sleep_fn=stop_after_one_sleep,
        clear_screen=lambda: events.append("clear"),
    )

    assert events == ["list", "clear", "sleep"]


def test_positive_interval_rejects_zero() -> None:
    with pytest.raises(Exception, match="greater than zero"):
        positive_interval("0")


def test_clear_terminal_uses_full_screen_clear(capsys) -> None:
    clear_terminal()

    assert capsys.readouterr().out == "\033[2J\033[3J\033[H"


def test_friendly_error_for_missing_modal_cli() -> None:
    assert "Modal CLI was not found" in friendly_error(FileNotFoundError())
