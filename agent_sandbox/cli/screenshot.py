import sys
from pathlib import Path

from agent_sandbox import SandboxToolPolicy, SandboxTools
from agent_sandbox.search import first_search_result
from agent_sandbox.urls import is_valid_url


def main(argv: list[str] | None = None) -> int:
    """Screenshots a web page or search result.

    Args:
        argv: Optional command-line words.

    Returns:
        Zero when the screenshot is saved.
    """

    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("Usage: agent-sandbox-screenshot <url or search terms>")

    text = " ".join(argv)
    url = text if is_valid_url(text) else first_search_result(text)
    print(f"Screenshot target: {url}")

    result = SandboxTools(
        policy=SandboxToolPolicy(allowed_tools=("browser",)),
        artifact_dir=Path("artifacts"),
    ).screenshot(url)
    if result.error:
        print(result.error, file=sys.stderr)
    if result.image_path is not None:
        print(f"Screenshot saved to {result.image_path.resolve()}")
    if result.text_path is not None:
        print(f"Observation saved to {result.text_path.resolve()}")
    return int(result.status != "succeeded")


if __name__ == "__main__":
    raise SystemExit(main())
