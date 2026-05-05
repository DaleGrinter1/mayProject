from dataclasses import dataclass
from pathlib import Path

from mayproject.sandbox.images import get_image
from mayproject.sandbox.runner import ModalSandboxRunner
from mayproject.sandbox.types import RunnerFactory, SandboxSpec


SCREENSHOT_SCRIPT_PATH = Path(__file__).parent / "scripts" / "screenshot_page.py"


@dataclass(frozen=True)
class BrowserConfig:
    remote_script_path: str = "/tmp/screenshot.py"
    remote_image_path: str = "/tmp/screenshot.png"
    remote_text_path: str = "/tmp/observation.txt"
    timeout: int = 600
    idle_timeout: int = 120


@dataclass(frozen=True)
class BrowserPrimitive:
    app_name: str = "my-app"
    config: BrowserConfig = BrowserConfig()
    runner_factory: RunnerFactory = ModalSandboxRunner

    def capture_page(self, url: str, image_path: Path, text_path: Path) -> None:
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
