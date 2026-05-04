from dataclasses import dataclass
from pathlib import Path

from mayproject.primitives.browser import BrowserCaptureResult, BrowserPrimitive
from mayproject.sandbox.results import DEFAULT_RUN_ROOT, SandboxRun


@dataclass(frozen=True)
class ScreenshotResult:
    url: str
    image_path: Path
    text_path: Path
    run: SandboxRun
    status: str


def capture_url(
    url: str,
    output_dir: Path = DEFAULT_RUN_ROOT,
    browser: BrowserPrimitive | None = None,
) -> ScreenshotResult:
    browser = browser or BrowserPrimitive(run_root=output_dir)
    capture: BrowserCaptureResult = browser.capture_page(url)

    return ScreenshotResult(
        url=url,
        image_path=capture.image_path,
        text_path=capture.text_path,
        run=capture.run,
        status=capture.status,
    )

