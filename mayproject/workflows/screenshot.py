from dataclasses import dataclass
from pathlib import Path
from time import time
from urllib.parse import urlparse

from mayproject.primitives.browser import BrowserPrimitive


@dataclass(frozen=True)
class ScreenshotResult:
    url: str
    image_path: Path
    text_path: Path


def screenshot_path(url: str, output_dir: Path = Path("screenshots")) -> Path:
    output_dir.mkdir(exist_ok=True)

    host = urlparse(url).netloc or "screenshot"
    safe_host = "".join(c if c.isalnum() or c in ".-" else "-" for c in host)
    return output_dir / f"{safe_host}-{int(time())}.png"


def capture_url(
    url: str,
    output_dir: Path = Path("screenshots"),
    browser: BrowserPrimitive | None = None,
) -> ScreenshotResult:
    image_path = screenshot_path(url, output_dir)
    text_path = image_path.with_suffix(".txt")
    browser = browser or BrowserPrimitive()

    browser.capture_page(url, image_path, text_path)

    return ScreenshotResult(url=url, image_path=image_path, text_path=text_path)

