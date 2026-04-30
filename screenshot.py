import sys

from mayproject.search import first_search_result
from mayproject.urls import is_valid_url
from mayproject.workflows.screenshot import capture_url


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: uv run python screenshot.py <url or search terms>")

    text = " ".join(sys.argv[1:])
    url = text if is_valid_url(text) else first_search_result(text)
    print(f"Screenshot target: {url}")

    result = capture_url(url)
    print(f"Screenshot saved to {result.image_path.resolve()}")
    print(f"Observation saved to {result.text_path.resolve()}")
