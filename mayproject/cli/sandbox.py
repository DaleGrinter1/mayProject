import argparse
import sys

from mayproject.workflows.sandbox import ManagedSandbox, parse_volume_mount


def main(argv: list[str] | None = None) -> int:
    """Runs the remote computer command line tool."""

    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    manager = ManagedSandbox(app_name=args.app_name)

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

    parser.error("Unknown sandbox action")


def build_parser() -> argparse.ArgumentParser:
    """Builds the command line choices for the remote computer."""

    parser = argparse.ArgumentParser(prog="may-sandbox")
    parser.add_argument("--app-name", default="my-app")
    subparsers = parser.add_subparsers(dest="action", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("--name", required=True)
    create.add_argument("--image", choices=["python", "browser"], default="python")
    create.add_argument("--volume", action="append", default=[])
    create.add_argument("--timeout", type=int, default=600)
    create.add_argument("--idle-timeout", type=int, default=120)

    status = subparsers.add_parser("status")
    add_sandbox_reference(status)

    execute = subparsers.add_parser("exec")
    add_sandbox_reference(execute)
    execute.add_argument("command", nargs=argparse.REMAINDER)

    shell = subparsers.add_parser("shell")
    add_sandbox_reference(shell)

    terminate = subparsers.add_parser("terminate")
    add_sandbox_reference(terminate)

    return parser


def add_sandbox_reference(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--name")
    group.add_argument("--id")


def strip_command_separator(command: list[str]) -> list[str]:
    if command[:1] == ["--"]:
        return command[1:]
    return command


def print_handle(label: str, handle: object) -> None:
    print(label)
    print(f"  id: {handle.object_id}")
    print(f"  app: {handle.app_name}")
    if handle.name:
        print(f"  name: {handle.name}")
    print(f"  returncode: {handle.returncode}")


if __name__ == "__main__":
    raise SystemExit(main())
