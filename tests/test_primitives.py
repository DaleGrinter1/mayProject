import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from mayproject.primitives.shell import ShellPrimitive
from mayproject.urls import is_valid_url
from mayproject.workflows.screenshot import capture_url


TEST_TMP_ROOT = Path(".mayproject") / "test-tmp"


def workspace_temp_dir():
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = TEST_TMP_ROOT / uuid4().hex
    path.mkdir()
    return path


class UrlTests(unittest.TestCase):
    def test_is_valid_url_accepts_http_and_https(self):
        self.assertTrue(is_valid_url("https://example.com"))
        self.assertTrue(is_valid_url("http://example.com/path"))

    def test_is_valid_url_rejects_non_web_urls(self):
        self.assertFalse(is_valid_url("example.com"))
        self.assertFalse(is_valid_url("file:///tmp/example.txt"))


class ShellPrimitiveTests(unittest.TestCase):
    def test_shell_rejects_empty_command(self):
        with self.assertRaisesRegex(ValueError, "at least one argument"):
            ShellPrimitive().run(())


class FakeBrowser:
    def __init__(self, run_root: Path):
        from mayproject.primitives.browser import BrowserCaptureResult
        from mayproject.sandbox.results import Artifact, SandboxResult, create_sandbox_run

        self.run = create_sandbox_run("browser-capture", run_root=run_root, run_id="abc12345")
        self.image_path = self.run.artifact_dir / "screenshot.png"
        self.text_path = self.run.artifact_dir / "observation.txt"
        result = SandboxResult(
            run=self.run.complete("succeeded"),
            status="succeeded",
            output={"url": "https://example.com"},
            artifacts=(
                Artifact("screenshot", "image", self.image_path, "image/png"),
                Artifact("observation", "text", self.text_path, "text/plain"),
            ),
        )
        self.capture = BrowserCaptureResult(
            url="https://example.com",
            image_path=self.image_path,
            text_path=self.text_path,
            result=result,
        )

    def capture_page(self, url: str):
        return self.capture


class ScreenshotWorkflowTests(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)

    def test_capture_url_returns_browser_result_paths(self):
        temp_dir = workspace_temp_dir()
        try:
            browser = FakeBrowser(temp_dir)
            result = capture_url("https://example.com", browser=browser)

            self.assertEqual(result.status, "succeeded")
            self.assertEqual(result.image_path.name, "screenshot.png")
            self.assertEqual(result.text_path.name, "observation.txt")
            self.assertEqual(result.run.run_id, "abc12345")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
