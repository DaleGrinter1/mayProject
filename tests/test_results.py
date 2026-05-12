"""Tests for filesystem-safe run records and serialized sandbox results."""

import json
import shutil
import unittest
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from agent_sandbox.sandbox.results import (
    Artifact,
    SandboxResult,
    create_sandbox_run,
    safe_slug,
)


TEST_TMP_ROOT = Path(".agent-sandbox") / "test-tmp"


def workspace_temp_dir() -> Path:
    """Create an isolated temporary directory under the project run root.

    Returns:
        A new directory path that the caller can remove after the test.
    """

    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = TEST_TMP_ROOT / uuid4().hex
    path.mkdir()
    return path


class SandboxResultsTests(unittest.TestCase):
    """Unit tests for sandbox run/result data models."""

    def tearDown(self) -> None:
        """Remove temporary run directories created by each test."""

        shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)

    def test_safe_slug_is_filesystem_friendly(self) -> None:
        """Verify arbitrary labels become stable path-safe slugs."""

        self.assertEqual(safe_slug("Browser Capture!"), "browser-capture")
        self.assertEqual(safe_slug("  ***  "), "task")

    def test_create_sandbox_run_uses_stable_directory_shape(self) -> None:
        """Verify run directories encode time, task kind, and run ID."""

        temp_dir = workspace_temp_dir()
        try:
            started_at = datetime(2026, 5, 4, 1, 2, 3, tzinfo=UTC)
            run = create_sandbox_run(
                "Browser Capture",
                run_root=temp_dir,
                started_at=started_at,
                run_id="ABC xyz!",
                tags={"agent": "local"},
                metadata={"url": "https://example.com"},
            )

            self.assertEqual(run.run_id, "ABC xyz!")
            self.assertEqual(run.task_kind, "Browser Capture")
            self.assertTrue(run.artifact_dir.exists())
            self.assertEqual(
                run.artifact_dir.name,
                "20260504T010203Z-browser-capture-abc-xyz",
            )
            self.assertEqual(run.status, "created")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_sandbox_result_serializes_paths_and_artifacts(self) -> None:
        """Verify sandbox results write JSON-friendly paths and artifacts."""

        temp_dir = workspace_temp_dir()
        try:
            run = create_sandbox_run("shell", run_root=temp_dir, run_id="abc12345")
            stdout_path = run.artifact_dir / "stdout.txt"
            result = SandboxResult(
                run=run.complete("succeeded"),
                status="succeeded",
                output={"returncode": 0},
                artifacts=(Artifact("stdout", "text", stdout_path, "text/plain"),),
                stdout="ok",
            )

            result_path = run.artifact_dir / "result.json"
            result.write_json(result_path)

            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "succeeded")
            self.assertEqual(data["output"], {"returncode": 0})
            self.assertEqual(data["artifacts"][0]["path"], str(stdout_path))
            self.assertEqual(data["run"]["status"], "succeeded")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
