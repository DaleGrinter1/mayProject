"""Golden-path SDK demo for a real Modal-backed environment."""

from __future__ import annotations

import argparse
import json
import sys

from agent_sandbox import SandboxToolPolicy, SandboxTools, ToolResult


def main(argv: list[str] | None = None) -> int:
    """Run a small shell, Python, and browser sequence.

    Args:
        argv: Optional command-line words.

    Returns:
        Zero when every selected tool succeeds.
    """

    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    tools = SandboxTools(
        app_name=args.app_name,
        policy=SandboxToolPolicy(
            allowed_tools=("shell", "python", "browser"),
            allowed_shell_commands=("python",),
            allowed_browser_domains=(args.domain,),
            max_timeout=args.max_timeout,
        ),
        record_runs=args.record_run,
    )

    results: list[ToolResult] = [
        tools.shell(["python", "--version"], timeout=args.max_timeout),
        tools.python_code("print('hello from a sandboxed Python tool')"),
    ]
    if not args.skip_screenshot:
        results.append(tools.screenshot(f"https://{args.domain}"))

    print(json.dumps([result.to_dict() for result in results], indent=2, sort_keys=True))
    return int(any(result.status != "succeeded" for result in results))


def build_parser() -> argparse.ArgumentParser:
    """Build the demo parser.

    Returns:
        Parser for golden-path demo arguments.
    """

    parser = argparse.ArgumentParser(prog="golden_path_demo.py")
    parser.add_argument("--app-name", default="my-app")
    parser.add_argument("--domain", default="example.com")
    parser.add_argument("--max-timeout", type=int, default=60)
    parser.add_argument("--record-run", action="store_true")
    parser.add_argument("--skip-screenshot", action="store_true")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
