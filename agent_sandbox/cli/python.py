import argparse
import sys
from pathlib import Path

from agent_sandbox import SandboxToolPolicy, SandboxTools
from agent_sandbox.cli.output import print_json


def main(argv: list[str] | None = None) -> int:
    """Runs a Python file on a remote computer.

    Args:
        argv: Optional command-line words.

    Returns:
        The remote command's finish code.
    """

    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    if not args.script:
        raise SystemExit("Usage: agent-sandbox-python <script.py> [args...]")

    script_path = Path(args.script)
    result = SandboxTools(
        policy=SandboxToolPolicy(allowed_tools=("python",)),
        record_runs=args.record_run,
    ).python_script(script_path, *args.script_args)
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
    """Build the one-shot Python command parser.

    Returns:
        Parser for Python script arguments.
    """

    parser = argparse.ArgumentParser(prog="agent-sandbox-python")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--record-run", action="store_true")
    parser.add_argument("script", nargs="?")
    parser.add_argument("script_args", nargs=argparse.REMAINDER)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
