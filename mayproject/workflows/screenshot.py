from dataclasses import dataclass
from pathlib import Path
from time import time
from urllib.parse import urlparse

from mayproject.primitives.browser import BrowserPrimitive


@dataclass(frozen=True)
class ScreenshotResult:
    """Shows where a screenshot and its notes were saved.

    Attributes:
        url: The web page that was captured.
        image_path: Where the screenshot was saved.
        text_path: Where the page notes were saved.
    """

    url: str
    image_path: Path
    text_path: Path


def screenshot_path(url: str, output_dir: Path = Path("screenshots")) -> Path:
    """Chooses a safe file name for a screenshot.

    Args:
        url: The web page being captured.
        output_dir: The folder for screenshot files.

    Returns:
        The local screenshot file path.
    """

    output_dir.mkdir(exist_ok=True)

    host = urlparse(url).netloc or "screenshot"
    safe_host = "".join(c if c.isalnum() or c in ".-" else "-" for c in host)
    return output_dir / f"{safe_host}-{int(time())}.png"


def capture_url(
    url: str,
    output_dir: Path = Path("screenshots"),
    browser: BrowserPrimitive | None = None,
) -> ScreenshotResult:
    """Takes a screenshot and saves notes about the page.

    Args:
        url: The web page to capture.
        output_dir: The folder for output files.
        browser: Optional browser helper for tests or custom use.

    Returns:
        The saved screenshot and notes paths.
    """

    image_path = screenshot_path(url, output_dir)
    text_path = image_path.with_suffix(".txt")
    browser = browser or BrowserPrimitive()

    browser.capture_page(url, image_path, text_path)

    return ScreenshotResult(url=url, image_path=image_path, text_path=text_path)
