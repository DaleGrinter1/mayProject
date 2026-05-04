from dataclasses import dataclass
from pathlib import Path

from mayproject.sandbox.images import browser_image
from mayproject.sandbox.runner import ModalSandboxRunner, SandboxSpec
from mayproject.sandbox.results import (
    DEFAULT_RUN_ROOT,
    Artifact,
    SandboxResult,
    create_sandbox_run,
)


SCREENSHOT_SCRIPT_PATH = Path(__file__).parent / "scripts" / "screenshot_page.py"


@dataclass(frozen=True)
class BrowserCaptureResult:
    url: str
    image_path: Path
    text_path: Path
    result: SandboxResult

    @property
    def run(self):
        return self.result.run

    @property
    def status(self) -> str:
        return self.result.status

    def to_dict(self):
        data = self.result.to_dict()
        data["url"] = self.url
        data["image_path"] = str(self.image_path)
        data["text_path"] = str(self.text_path)
        return data


@dataclass(frozen=True)
class BrowserPrimitive:
    app_name: str = "my-app"
    run_root: Path = DEFAULT_RUN_ROOT

    def capture_page(self, url: str) -> BrowserCaptureResult:
        run = create_sandbox_run(
            "browser-capture",
            run_root=self.run_root,
            tags={"primitive": "browser", "workflow": "screenshot"},
            metadata={"url": url},
        )
        image_path = run.artifact_dir / "screenshot.png"
        text_path = run.artifact_dir / "observation.txt"

        spec = SandboxSpec(
            app_name=self.app_name,
            image=browser_image(),
            tags={"primitive": "browser", "workflow": "screenshot"},
        )

        with ModalSandboxRunner(spec) as runner:
            runner.copy_from_local(SCREENSHOT_SCRIPT_PATH, "/tmp/screenshot.py")
            command_result = runner.exec(
                "python",
                "/tmp/screenshot.py",
                url,
                "/tmp/screenshot.png",
                "/tmp/observation.txt",
            )

            if command_result.returncode != 0:
                completed_run = run.complete("failed")
                result = SandboxResult(
                    run=completed_run,
                    status="failed",
                    output={"url": url, "returncode": command_result.returncode},
                    stdout=command_result.stdout,
                    stderr=command_result.stderr,
                    error=f"Screenshot command failed with return code {command_result.returncode}",
                )
                result.write_json(run.artifact_dir / "result.json")
                result.run.write_json(run.artifact_dir / "metadata.json")
                return BrowserCaptureResult(
                    url=url,
                    image_path=image_path,
                    text_path=text_path,
                    result=result,
                )

            runner.copy_to_local("/tmp/screenshot.png", image_path)
            runner.copy_to_local("/tmp/observation.txt", text_path)

        artifacts = (
            Artifact("screenshot", "image", image_path, "image/png"),
            Artifact("observation", "text", text_path, "text/plain"),
        )
        completed_run = run.complete("succeeded")
        result = SandboxResult(
            run=completed_run,
            status="succeeded",
            output={"url": url},
            artifacts=artifacts,
            stdout=command_result.stdout,
            stderr=command_result.stderr,
        )
        result.write_json(run.artifact_dir / "result.json")
        result.run.write_json(run.artifact_dir / "metadata.json")
        return BrowserCaptureResult(
            url=url,
            image_path=image_path,
            text_path=text_path,
            result=result,
        )
