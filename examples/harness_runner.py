"""Small harness-style runner around the public agent-sandbox SDK.

This is intentionally an example, not a package entry point. It shows how an
external agent harness can choose a tool, grant only that tool in policy, run
the sandbox-backed operation, and emit a structured JSON result.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent_sandbox import (
    SandboxToolPolicy,
    SandboxToolRegistry,
    SandboxTools,
    ToolResult,
)


def main(argv: list[str] | None = None) -> int:
    """Run one sandbox-backed tool call and print its JSON result.

    Args:
        argv: Optional command-line words.

    Returns:
        Process-style exit code for the selected tool call.
    """

    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    result = run_tool(args)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    if result.returncode is not None:
        return result.returncode
    return int(result.status != "succeeded")


def build_parser() -> argparse.ArgumentParser:
    """Build the example harness parser.

    Returns:
        Parser for harness example arguments.
    """

    parser = argparse.ArgumentParser(
        prog="harness_runner.py",
        description="Run one agent-sandbox SDK tool call and print JSON.",
    )
    parser.add_argument("--app-name", default="my-app")
    parser.add_argument("--record-run", action="store_true")

    commands = parser.add_subparsers(dest="tool", required=True)

    shell = commands.add_parser("shell", help="Run a shell command.")
    shell.add_argument("command", nargs=argparse.REMAINDER)

    python_code = commands.add_parser("python-code", help="Run Python source.")
    python_code.add_argument("code")
    python_code.add_argument("args", nargs=argparse.REMAINDER)

    python_script = commands.add_parser("python-script", help="Run a Python file.")
    python_script.add_argument("script_path", type=Path)
    python_script.add_argument("args", nargs=argparse.REMAINDER)

    screenshot = commands.add_parser("screenshot", help="Capture a web page.")
    screenshot.add_argument("url")
    screenshot.add_argument("--output-dir", type=Path)

    return parser


def run_tool(args: argparse.Namespace) -> ToolResult:
    """Run the SDK tool selected by parsed arguments.

    Args:
        args: Parsed example harness arguments.

    Returns:
        Structured SDK result.
    """

    registry = SandboxToolRegistry(
        SandboxTools(
            app_name=args.app_name,
            policy=SandboxToolPolicy(allowed_tools=(policy_tool(args.tool),)),
            record_runs=args.record_run,
        )
    )

    match args.tool:
        case "shell":
            command = strip_separator(args.command)
            if not command:
                raise SystemExit("Usage: harness_runner.py shell -- <command> [args...]")
            return registry.call_tool("shell", {"command": command})
        case "python-code":
            return registry.call_tool(
                "python_code",
                {"code": args.code, "args": strip_separator(args.args)},
            )
        case "python-script":
            return registry.call_tool(
                "python_script",
                {
                    "script_path": str(args.script_path),
                    "args": strip_separator(args.args),
                },
            )
        case "screenshot":
            arguments = {"url": args.url}
            if args.output_dir:
                arguments["output_dir"] = str(args.output_dir)
            return registry.call_tool("screenshot", arguments)

    raise SystemExit(f"Unknown tool: {args.tool}")


def policy_tool(command_name: str) -> str:
    """Map an example command name to the SDK policy tool name.

    Args:
        command_name: Parsed subcommand name.

    Returns:
        Tool name accepted by `SandboxToolPolicy`.
    """

    if command_name in {"python-code", "python-script"}:
        return "python"
    if command_name == "screenshot":
        return "browser"
    return command_name


def strip_separator(values: list[str]) -> list[str]:
    """Remove an optional `--` separator from remaining arguments.

    Args:
        values: Raw trailing arguments parsed by argparse.

    Returns:
        Trailing arguments without the separator.
    """

    if values[:1] == ["--"]:
        return values[1:]
    return values


if __name__ == "__main__":
    raise SystemExit(main())
