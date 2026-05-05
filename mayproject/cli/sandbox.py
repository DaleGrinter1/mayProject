import argparse
import sys
from collections.abc import Callable
from time import sleep

import modal

from mayproject.workflows.doctor import DoctorCheck, run_doctor
from mayproject.workflows.sandbox import ManagedSandbox, parse_volume_mount


def main(argv: list[str] | None = None) -> int:
    """Runs the remote computer command line tool."""

    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    manager = ManagedSandbox(app_name=args.app_name)
    try:
        return run_command(args, manager)
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 130
    except (ValueError, FileNotFoundError, modal.exception.Error) as exc:
        print(f"Error: {friendly_error(exc)}", file=sys.stderr)
        return 1


def run_command(args: argparse.Namespace, manager: ManagedSandbox) -> int:
    """Runs the command the person chose."""

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
        print_handle("Sandbox status", manager.status(name=args.name, sandbox_id=args.id))
        return 0

    if args.action == "list":
        if args.watch:
            watch_handles(manager, args.interval)
            return 0
        print_handles(manager.list())
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


def build_parser() -> argparse.ArgumentParser:
    """Builds the command line choices for the remote computer."""

    parser = argparse.ArgumentParser(prog="may-sandbox")
    parser.add_argument("--app-name", default="my-app")
    subparsers = parser.add_subparsers(dest="action", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("--name", required=True)
    create.add_argument("--image", choices=["python", "browser", "dev"], default="python")
    create.add_argument("--volume", action="append", default=[])
    create.add_argument("--timeout", type=int, default=600)
    create.add_argument("--idle-timeout", type=int, default=120)

    status = subparsers.add_parser("status")
    add_sandbox_reference(status)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--watch", action="store_true")
    list_parser.add_argument("--interval", type=positive_interval, default=2.0)

    subparsers.add_parser("doctor")

    execute = subparsers.add_parser("exec")
    add_sandbox_reference(execute)
    execute.add_argument("command", nargs=argparse.REMAINDER)

    shell = subparsers.add_parser("shell")
    add_sandbox_reference(shell)

    terminate = subparsers.add_parser("terminate")
    add_sandbox_reference(terminate)

    subparsers.add_parser("terminate-all")

    return parser


def add_sandbox_reference(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--name")
    group.add_argument("--id")


def strip_command_separator(command: list[str]) -> list[str]:
    if command[:1] == ["--"]:
        return command[1:]
    return command


def positive_interval(text: str) -> float:
    value = float(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("interval must be greater than zero")
    return value


def print_handle(label: str, handle: object) -> None:
    print(label)
    print(f"  id: {handle.object_id}")
    print(f"  app: {handle.app_name}")
    if handle.name:
        print(f"  name: {handle.name}")
    if handle.tags.get("image"):
        print(f"  image: {handle.tags['image']}")
    print(f"  returncode: {handle.returncode}")


def print_handles(handles: list[object]) -> None:
    if not handles:
        print("No managed sandboxes found")
        return

    rows = [
        (
            handle.name or handle.tags.get("name", "-"),
            handle.tags.get("image", "-"),
            "running" if handle.returncode is None else f"done:{handle.returncode}",
            handle.object_id,
        )
        for handle in handles
    ]
    print_table(("Name", "Image", "State", "Sandbox ID"), rows)


def print_terminated(handles: list[object]) -> None:
    if not handles:
        print("No managed sandboxes found")
        return

    rows = [
        (
            handle.name or handle.tags.get("name", "-"),
            handle.tags.get("image", "-"),
            handle.object_id,
        )
        for handle in handles
    ]
    print_table(("Name", "Image", "Sandbox ID"), rows)
    print(f"Terminated {len(handles)} managed sandbox(es).")


def print_doctor(checks: list[DoctorCheck]) -> None:
    rows = [
        (check.name, "ok" if check.ok else "needs help", check.message)
        for check in checks
    ]
    print_table(("Check", "Status", "Message"), rows)


def watch_handles(
    manager: ManagedSandbox,
    interval: float,
    sleep_fn: Callable[[float], object] | None = None,
    clear_screen: Callable[[], object] | None = None,
) -> None:
    """Refreshes the remote computer list until you stop it."""

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
    sys.stdout.write("\033[2J\033[3J\033[H")
    sys.stdout.flush()


def print_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    widths = [
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    ]
    border = "+-" + "-+-".join("-" * width for width in widths) + "-+"
    header = "| " + " | ".join(
        text.ljust(widths[index]) for index, text in enumerate(headers)
    ) + " |"

    print(border)
    print(header)
    print(border)
    for row in rows:
        print(
            "| "
            + " | ".join(text.ljust(widths[index]) for index, text in enumerate(row))
            + " |"
        )
    print(border)


def friendly_error(exc: BaseException) -> str:
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
