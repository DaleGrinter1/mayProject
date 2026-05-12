import argparse
import sys
from pathlib import Path

from agent_sandbox import SandboxToolPolicy, SandboxTools
from agent_sandbox.cli.output import print_json
from agent_sandbox.search import first_search_result
from agent_sandbox.urls import is_valid_url


def main(argv: list[str] | None = None) -> int:
    """Screenshots a web page or search result.

    Args:
        argv: Optional command-line words.

    Returns:
        Zero when the screenshot is saved.
    """

    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    if not args.target:
        raise SystemExit("Usage: agent-sandbox-screenshot <url or search terms>")

    text = " ".join(args.target)
    url = text if is_valid_url(text) else first_search_result(text)
    if not args.json:
        print(f"Screenshot target: {url}")

    result = SandboxTools(
        policy=SandboxToolPolicy(allowed_tools=("browser",)),
        artifact_dir=Path("artifacts"),
        record_runs=args.record_run,
    ).screenshot(url)
    if args.json:
        print_json(result.to_dict())
        return int(result.status != "succeeded")

    if result.error:
        print(result.error, file=sys.stderr)
    if result.image_path is not None:
        print(f"Screenshot saved to {result.image_path.resolve()}")
    if result.text_path is not None:
        print(f"Observation saved to {result.text_path.resolve()}")
    return int(result.status != "succeeded")


def build_parser() -> argparse.ArgumentParser:
    """Build the one-shot screenshot command parser.

    Returns:
        Parser for screenshot arguments.
    """

    parser = argparse.ArgumentParser(prog="agent-sandbox-screenshot")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--record-run", action="store_true")
    parser.add_argument("target", nargs="*")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
