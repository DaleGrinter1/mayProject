from dataclasses import dataclass
from pathlib import Path

from mayproject.sandbox.images import browser_image
from mayproject.sandbox.runner import ModalSandboxRunner, SandboxSpec


SCREENSHOT_SCRIPT_PATH = Path(__file__).parent / "scripts" / "screenshot_page.py"


@dataclass(frozen=True)
class BrowserPrimitive:
    app_name: str = "my-app"

    def capture_page(self, url: str, image_path: Path, text_path: Path) -> None:
        spec = SandboxSpec(
            app_name=self.app_name,
            image=browser_image(),
            tags={"primitive": "browser", "workflow": "screenshot"},
        )

        with ModalSandboxRunner(spec) as runner:
            runner.copy_from_local(SCREENSHOT_SCRIPT_PATH, "/tmp/screenshot.py")
            result = runner.exec(
                "python",
                "/tmp/screenshot.py",
                url,
                "/tmp/screenshot.png",
                "/tmp/observation.txt",
            )

            if result.returncode != 0:
                raise RuntimeError(f"Screenshot failed in sandbox:\n{result.stderr}")

            runner.copy_to_local("/tmp/screenshot.png", image_path)
            runner.copy_to_local("/tmp/observation.txt", text_path)
