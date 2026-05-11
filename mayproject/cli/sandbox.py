import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from time import sleep

import modal

from mayproject.config import load_config
from mayproject.cli.output import (
    handle_payload,
    print_doctor,
    print_handle,
    print_handles,
    print_inspection,
    print_json,
    print_terminated,
)
from mayproject.search import first_search_result
from mayproject.urls import is_valid_url
from mayproject.workflows.doctor import DoctorCheck, run_doctor
from mayproject.workflows.sandbox import ManagedSandbox, parse_volume_mount


def main(argv: list[str] | None = None) -> int:
    """Runs the remote computer command line tool.

    Args:
        argv: Optional command-line words.

    Returns:
        The command's finish code.
    """

    config = load_config()
    parser = build_parser(default_app_name=config.app_name)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    manager = ManagedSandbox(app_name=args.app_name)
    try:
        return run_command(args, manager, config.artifacts_dir)
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 130
    except (ValueError, FileNotFoundError, modal.exception.Error) as exc:
        print(f"Error: {friendly_error(exc)}", file=sys.stderr)
        return 1


def run_command(
    args: argparse.Namespace,
    manager: ManagedSandbox,
    artifacts_dir: Path = Path("artifacts"),
) -> int:
    """Runs the command the person chose.

    Args:
        args: Parsed command-line choices.
        manager: The remote computer manager.
        artifacts_dir: The local folder for generated and copied files.

    Returns:
        The command's finish code.
    """

    if args.action == "create":
        handle = manager.create(
            name=args.name,
            image_name=args.image,
            volume_mounts=[parse_volume_mount(text) for text in args.volume],
            timeout=args.timeout,
            idle_timeout=args.idle_timeout,
        )
        print_handle("Sandbox ready", handle)
        return 0

    if args.action == "status":
        handle = manager.status(name=args.name, sandbox_id=args.id)
        if args.json:
            print_json(handle_payload(handle))
        else:
            print_handle("Sandbox status", handle)
        return 0

    if args.action == "inspect":
        handle = manager.status(name=args.name, sandbox_id=args.id)
        if args.json:
            print_json(handle_payload(handle))
        else:
            print_inspection(handle)
        return 0

    if args.action == "list":
        if args.watch:
            watch_handles(manager, args.interval)
            return 0
        handles = manager.list()
        if args.json:
            print_json([handle_payload(handle) for handle in handles])
        else:
            print_handles(handles)
        return 0

    if args.action == "doctor":
        print_doctor(run_doctor())
        return 0

    if args.action == "exec":
        command = strip_command_separator(args.command)
        result = manager.exec(command, name=args.name, sandbox_id=args.id)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return result.returncode

    if args.action in ("copy-to", "put"):
        manager.copy_to(
            Path(args.local_path),
            args.remote_path,
            name=args.name,
            sandbox_id=args.id,
        )
        print(f"Copied {args.local_path} to {args.remote_path}")
        return 0

    if args.action in ("copy-from", "get"):
        manager.copy_from(
            args.remote_path,
            Path(args.local_path),
            name=args.name,
            sandbox_id=args.id,
        )
        print(f"Copied {args.remote_path} to {args.local_path}")
        return 0

    if args.action == "screenshot":
        text = " ".join(args.target)
        url = text if is_valid_url(text) else first_search_result(text)
        output_dir = Path(args.output_dir) if args.output_dir else artifacts_dir / "screenshots"
        print(f"Screenshot target: {url}")
        result = manager.screenshot(
            url,
            output_dir=output_dir,
            name=args.name,
            sandbox_id=args.id,
        )
        print(f"Screenshot saved to {result.image_path.resolve()}")
        print(f"Observation saved to {result.text_path.resolve()}")
        return 0

    if args.action == "logs":
        result = manager.logs(name=args.name, sandbox_id=args.id)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return result.returncode

    if args.action == "shell":
        return manager.shell(name=args.name, sandbox_id=args.id)

    if args.action == "terminate":
        returncode = manager.terminate(name=args.name, sandbox_id=args.id)
        print(f"Sandbox terminated: {returncode}")
        return 0

    if args.action == "terminate-all":
        print_terminated(manager.terminate_all())
        return 0

    raise ValueError("Unknown sandbox action")


def build_parser(default_app_name: str = "my-app") -> argparse.ArgumentParser:
    """Builds the command line choices for the remote computer.

    Args:
        default_app_name: The Modal app name to use when no flag is passed.

    Returns:
        The command-line parser.
    """

    parser = argparse.ArgumentParser(prog="may-sandbox")
    parser.add_argument("--app-name", default=default_app_name)
    subparsers = parser.add_subparsers(dest="action", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("--name", required=True)
    create.add_argument("--image", choices=["python", "browser", "dev"], default="python")
    create.add_argument("--volume", action="append", default=[])
    create.add_argument("--timeout", type=int, default=600)
    create.add_argument("--idle-timeout", type=int, default=120)

    status = subparsers.add_parser("status")
    add_sandbox_reference(status)
    status.add_argument("--json", action="store_true")

    inspect = subparsers.add_parser("inspect")
    add_sandbox_reference(inspect)
    inspect.add_argument("--json", action="store_true")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--watch", action="store_true")
    list_parser.add_argument("--interval", type=positive_interval, default=2.0)
    list_parser.add_argument("--json", action="store_true")

    subparsers.add_parser("doctor")

    execute = subparsers.add_parser("exec")
    add_sandbox_reference(execute)
    execute.add_argument("command", nargs=argparse.REMAINDER)

    copy_to = subparsers.add_parser("copy-to")
    add_sandbox_reference(copy_to)
    copy_to.add_argument("local_path")
    copy_to.add_argument("remote_path")

    put = subparsers.add_parser("put")
    add_sandbox_reference(put)
    put.add_argument("local_path")
    put.add_argument("remote_path")

    copy_from = subparsers.add_parser("copy-from")
    add_sandbox_reference(copy_from)
    copy_from.add_argument("remote_path")
    copy_from.add_argument("local_path")

    get = subparsers.add_parser("get")
    add_sandbox_reference(get)
    get.add_argument("remote_path")
    get.add_argument("local_path")

    screenshot = subparsers.add_parser("screenshot")
    add_sandbox_reference(screenshot)
    screenshot.add_argument("--output-dir")
    screenshot.add_argument("target", nargs="+")

    logs = subparsers.add_parser("logs")
    add_sandbox_reference(logs)

    shell = subparsers.add_parser("shell")
    add_sandbox_reference(shell)

    terminate = subparsers.add_parser("terminate")
    add_sandbox_reference(terminate)

    subparsers.add_parser("terminate-all")

    return parser


def add_sandbox_reference(parser: argparse.ArgumentParser) -> None:
    """Adds name or ID choices to a command.

    Args:
        parser: The command parser to update.
    """

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--name")
    group.add_argument("--id")


def strip_command_separator(command: list[str]) -> list[str]:
    """Removes the extra marker before a command.

    Args:
        command: Command words from the command line.

    Returns:
        Command words without the `--` marker.
    """

    if command[:1] == ["--"]:
        return command[1:]
    return command


def positive_interval(text: str) -> float:
    """Checks that a refresh speed is above zero.

    Args:
        text: The interval text from the command line.

    Returns:
        The interval as a number.
    """

    value = float(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("interval must be greater than zero")
    return value


def watch_handles(
    manager: ManagedSandbox,
    interval: float,
    sleep_fn: Callable[[float], object] | None = None,
    clear_screen: Callable[[], object] | None = None,
) -> None:
    """Refreshes the remote computer list until you stop it.

    Args:
        manager: The remote computer manager.
        interval: Seconds between refreshes.
        sleep_fn: Optional sleep function for tests.
        clear_screen: Optional screen clear function for tests.
    """

    sleep_for = sleep_fn or sleep
    clear = clear_screen or clear_terminal

    try:
        while True:
            handles = manager.list()
            clear()
            print_handles(handles)
            print(f"\nRefreshing every {interval:g}s. Press Ctrl+C to stop.")
            sleep_for(interval)
    except KeyboardInterrupt:
        print("\nStopped watching sandboxes.")


def clear_terminal() -> None:
    """Clears the terminal before drawing a fresh table."""

    sys.stdout.write("\033[2J\033[3J\033[H")
    sys.stdout.flush()


def friendly_error(exc: BaseException) -> str:
    """Turns common errors into friendlier words.

    Args:
        exc: The error to explain.

    Returns:
        A plain message for the user.
    """

    if isinstance(exc, modal.exception.NotFoundError):
        return "I could not find that sandbox. Try `uv run may-sandbox list`."
    if isinstance(exc, modal.exception.AuthError):
        return "Modal is not logged in. Run `uv run modal token new`."
    if isinstance(exc, FileNotFoundError):
        return "Modal CLI was not found. Try running commands with `uv run`."
    message = str(exc).strip()
    if message:
        return message
    return exc.__class__.__name__


if __name__ == "__main__":
    raise SystemExit(main())
