from html.parser import HTMLParser
from pathlib import Path
import sys
from time import time
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

import modal


image = (
    modal.Image.debian_slim(python_version="3.13")
    .pip_install("playwright")
    .run_commands("python -m playwright install --with-deps chromium")
)

SCREENSHOT_PY = """
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1]
output_path = sys.argv[2]

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(2_000)
    page.screenshot(path=output_path, full_page=True)
    browser.close()
"""


class DuckDuckGoResultsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result_urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag != "a" or "result__a" not in attrs.get("class", ""):
            return

        href = attrs.get("href")
        if href:
            self.result_urls.append(clean_result_url(href))


def clean_result_url(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    return unquote(query["uddg"][0]) if "uddg" in query else url


def first_search_result(query: str) -> str:
    search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    request = Request(search_url, headers={"User-Agent": "Mozilla/5.0"})

    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")

    parser = DuckDuckGoResultsParser()
    parser.feed(html)

    if not parser.result_urls:
        raise RuntimeError(f"No search results found for: {query}")

    return parser.result_urls[0]


def is_valid_url(text: str) -> bool:
    parsed = urlparse(text)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def screenshot_path(url: str) -> Path:
    screenshots_dir = Path("screenshots")
    screenshots_dir.mkdir(exist_ok=True)

    host = urlparse(url).netloc or "screenshot"
    safe_host = "".join(c if c.isalnum() or c in ".-" else "-" for c in host)
    return screenshots_dir / f"{safe_host}-{int(time())}.png"


def screenshot_url(url: str) -> Path:
    app = modal.App.lookup("my-app", create_if_missing=True)
    local_path = screenshot_path(url)

    sandbox = modal.Sandbox.create(
        "sleep",
        "300",
        app=app,
        image=image,
        timeout=600,
        idle_timeout=120,
        verbose=True,
    )

    try:
        sandbox.filesystem.write_text(SCREENSHOT_PY, "/tmp/screenshot.py")
        process = sandbox.exec("python", "/tmp/screenshot.py", url, "/tmp/screenshot.png")
        process.wait()
        stderr = process.stderr.read()

        if process.returncode != 0:
            raise RuntimeError(f"Screenshot failed in sandbox:\n{stderr}")

        sandbox.filesystem.copy_to_local("/tmp/screenshot.png", local_path)
    finally:
        sandbox.terminate()
        sandbox.detach()

    return local_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: uv run python screenshot.py <url or search terms>")

    text = " ".join(sys.argv[1:])
    url = text if is_valid_url(text) else first_search_result(text)
    print(f"Screenshot target: {url}")

    saved_path = screenshot_url(url)
    print(f"Screenshot saved to {saved_path.resolve()}")
