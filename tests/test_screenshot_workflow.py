"""Tests for screenshot path generation and browser workflow delegation."""

from pathlib import Path

from agent_sandbox.workflows import screenshot as screenshot_workflow


class StubBrowser:
    """Records browser capture requests without launching a real sandbox."""

    def __init__(self) -> None:
        """Create an empty capture history."""

        self.calls: list[tuple[str, Path, Path]] = []

    def capture_page(self, url: str, image_path: Path, text_path: Path) -> None:
        """Record the requested capture paths.

        Args:
            url: URL the workflow asked the browser to capture.
            image_path: Local path where the screenshot should be written.
            text_path: Local path where observation text should be written.
        """

        self.calls.append((url, image_path, text_path))


def test_screenshot_path_uses_safe_host_and_output_dir(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify screenshot filenames include a sanitized host and timestamp."""

    monkeypatch.setattr(screenshot_workflow, "time", lambda: 123)

    path = screenshot_workflow.screenshot_path("https://example.com/a", tmp_path)

    assert path == tmp_path / "example.com-123.png"


def test_capture_url_uses_browser_and_returns_paths(tmp_path: Path, monkeypatch) -> None:
    """Verify capture_url delegates work and returns the expected local paths."""

    monkeypatch.setattr(screenshot_workflow, "time", lambda: 456)
    browser = StubBrowser()

    result = screenshot_workflow.capture_url(
        "https://example.com",
        output_dir=tmp_path,
        browser=browser,
    )

    assert result.image_path == tmp_path / "example.com-456.png"
    assert result.text_path == tmp_path / "example.com-456.txt"
    assert browser.calls == [
        ("https://example.com", result.image_path, result.text_path)
    ]
