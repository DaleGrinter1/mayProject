import sys

from mayproject.search import first_search_result
from mayproject.urls import is_valid_url
from mayproject.workflows.screenshot import capture_url


def main(argv: list[str] | None = None) -> int:
    """Screenshots a web page or search result.

    Args:
        argv: Optional command-line words.

    Returns:
        Zero when the screenshot is saved.
    """

    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("Usage: may-screenshot <url or search terms>")

    text = " ".join(argv)
    url = text if is_valid_url(text) else first_search_result(text)
    print(f"Screenshot target: {url}")

    result = capture_url(url)
    print(f"Run: {result.run.run_id} ({result.status})")
    print(f"Artifacts: {result.run.artifact_dir.resolve()}")
    print(f"Screenshot saved to {result.image_path.resolve()}")
    print(f"Observation saved to {result.text_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
