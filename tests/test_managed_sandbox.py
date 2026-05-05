import pytest

from mayproject.cli.sandbox import clear_terminal, main, positive_interval, watch_handles
from mayproject.sandbox.fake import FakeSandboxRunner
from mayproject.sandbox.types import CommandResult, SandboxSpec
from mayproject.workflows import sandbox as sandbox_workflow
from mayproject.workflows.sandbox import ManagedSandbox, parse_volume_mount


class MissingSandbox(Exception):
    pass


class RunnerRecorder:
    def __init__(self) -> None:
        self.runners: list[FakeSandboxRunner] = []

    def factory(self, spec: SandboxSpec) -> FakeSandboxRunner:
        runner = FakeSandboxRunner(spec)
        self.runners.append(runner)
        return runner


class FakeStream:
    def __init__(self, text: str) -> None:
        self.text = text

    def read(self) -> str:
        return self.text


class FakeProcess:
    def __init__(self, result: CommandResult) -> None:
        self.returncode: int | None = result.returncode
        self.stdout = FakeStream(result.stdout)
        self.stderr = FakeStream(result.stderr)

    def wait(self) -> None:
        return None


class FakeRemoteSandbox:
    def __init__(
        self,
        object_id: str = "sb-123",
        result: CommandResult | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        self.object_id = object_id
        self.result = result or CommandResult(0, "", "")
        self.tags = tags or {"managed": "true"}
        self.commands: list[tuple[str, ...]] = []
        self.detached = False
        self.terminated = False

    def hydrate(self) -> None:
        return None

    def get_tags(self) -> dict[str, str]:
        return self.tags

    def poll(self) -> int | None:
        return None

    def exec(self, *command: str) -> FakeProcess:
        self.commands.append(command)
        return FakeProcess(self.result)

    def terminate(self, wait: bool = False) -> int | None:
        self.terminated = wait
        return 0

    def detach(self) -> None:
        self.detached = True


class FakeConnector:
    def __init__(
        self,
        sandbox: FakeRemoteSandbox | None = None,
        sandboxes: list[FakeRemoteSandbox] | None = None,
    ) -> None:
        self.sandbox = sandbox
        self.sandboxes = sandboxes or []
        self.list_tags: dict[str, str] | None = None

    def from_name(self, app_name: str, name: str) -> FakeRemoteSandbox:
        if self.sandbox is None:
            raise MissingSandbox(name)
        return self.sandbox

    def from_id(self, sandbox_id: str) -> FakeRemoteSandbox:
        if self.sandbox is None:
            raise MissingSandbox(sandbox_id)
        return self.sandbox

    async def list(self, *, tags: dict[str, str]):
        self.list_tags = tags
        for sandbox in self.sandboxes:
            yield sandbox


class SyncListConnector(FakeConnector):
    def list(self, *, tags: dict[str, str]):
        self.list_tags = tags
        yield from self.sandboxes


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
    remote = FakeRemoteSandbox(result=CommandResult(7, "out", "err"))
    manager = ManagedSandbox(connector=FakeConnector(remote))

    result = manager.exec(["python", "--version"], name="devbox")

    assert result == CommandResult(7, "out", "err")
    assert remote.commands == [("python", "--version")]
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
