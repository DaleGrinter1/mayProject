from dataclasses import dataclass
from pathlib import Path

from mayproject.sandbox.images import get_image
from mayproject.sandbox.runner import ModalSandboxRunner
from mayproject.sandbox.types import RunnerFactory, SandboxSpec


SCREENSHOT_SCRIPT_PATH = Path(__file__).parent / "scripts" / "screenshot_page.py"


@dataclass(frozen=True)
class BrowserConfig:
    """Stores where browser files live on the remote computer.

    Attributes:
        remote_script_path: Where the browser script is copied.
        remote_image_path: Where the screenshot is saved remotely.
        remote_text_path: Where the page notes are saved remotely.
        timeout: How long the remote computer may run.
        idle_timeout: How long the remote computer may sit unused.
    """

    remote_script_path: str = "/tmp/screenshot.py"
    remote_image_path: str = "/tmp/screenshot.png"
    remote_text_path: str = "/tmp/observation.txt"
    timeout: int = 600
    idle_timeout: int = 120


@dataclass(frozen=True)
class BrowserPrimitive:
    """Uses a remote browser to look at a web page.

    Attributes:
        app_name: The Modal app name to use.
        config: The browser settings.
        runner_factory: Builds the remote computer runner.
    """

    app_name: str = "my-app"
    config: BrowserConfig = BrowserConfig()
    runner_factory: RunnerFactory = ModalSandboxRunner

    def capture_page(self, url: str, image_path: Path, text_path: Path) -> None:
        """Saves a screenshot and page notes for a web page.

        Args:
            url: The web page to open.
            image_path: Where to save the screenshot on this computer.
            text_path: Where to save the page notes on this computer.
        """

        spec = SandboxSpec(
            app_name=self.app_name,
            image=get_image("browser"),
            timeout=self.config.timeout,
            idle_timeout=self.config.idle_timeout,
            tags={"primitive": "browser", "workflow": "screenshot"},
        )

        with self.runner_factory(spec) as runner:
            runner.copy_from_local(SCREENSHOT_SCRIPT_PATH, self.config.remote_script_path)
            result = runner.exec(
                "python",
                self.config.remote_script_path,
                url,
                self.config.remote_image_path,
                self.config.remote_text_path,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Screenshot failed in sandbox:\n{result.stderr}")

            runner.copy_to_local(self.config.remote_image_path, image_path)
            runner.copy_to_local(self.config.remote_text_path, text_path)
