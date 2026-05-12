import argparse
import sys

from agent_sandbox import SandboxToolPolicy, SandboxTools
from agent_sandbox.cli.output import print_json


def main(argv: list[str] | None = None) -> int:
    """Runs one command on a remote computer.

    Args:
        argv: Optional command-line words.

    Returns:
        The remote command's finish code.
    """

    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    command = strip_command_separator(args.command)
    if not command:
        raise SystemExit("Usage: agent-sandbox-shell <command> [args...]")

    result = SandboxTools(
        policy=SandboxToolPolicy(allowed_tools=("shell",)),
        record_runs=args.record_run,
    ).shell(command)
    if args.json:
        print_json(result.to_dict())
        return result.returncode if result.returncode is not None else int(result.status != "succeeded")

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.error:
        print(result.error, file=sys.stderr)
    return result.returncode if result.returncode is not None else int(result.status != "succeeded")


def build_parser() -> argparse.ArgumentParser:
    """Build the one-shot shell command parser.

    Returns:
        Parser for shell command arguments.
    """

    parser = argparse.ArgumentParser(prog="agent-sandbox-shell")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--record-run", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def strip_command_separator(command: list[str]) -> list[str]:
    """Remove an optional `--` separator before command words.

    Args:
        command: Raw command words parsed by argparse.

    Returns:
        Command words suitable for sandbox execution.
    """

    if command[:1] == ["--"]:
        return command[1:]
    return command


if __name__ == "__main__":
    raise SystemExit(main())
