import os
from pathlib import Path
from uuid import uuid4

import pytest

from mayproject.workflows.sandbox import ManagedSandbox


ARTIFACTS_DIR = Path("artifacts")


pytestmark = pytest.mark.skipif(
    os.environ.get("MAYPROJECT_RUN_MODAL_TESTS") != "1",
    reason="set MAYPROJECT_RUN_MODAL_TESTS=1 to run real Modal integration tests",
)


def test_modal_sandbox_can_copy_remote_text_file_to_local() -> None:
    """Creates a real Modal sandbox and copies a text file back locally.
    """

    name = f"copy-test-{uuid4().hex[:8]}"
    remote_path = "/tmp/mayproject-copy-test.txt"
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    local_path = ARTIFACTS_DIR / f"{name}.txt"
    manager = ManagedSandbox()

    try:
        manager.create(name=name, image_name="python", timeout=300, idle_timeout=60)
        result = manager.exec(
            ["sh", "-lc", f"printf 'hello from modal\\n' > {remote_path}"],
            name=name,
        )

        assert result.returncode == 0

        manager.copy_from(remote_path, local_path, name=name)

        assert local_path.read_text(encoding="utf-8") == "hello from modal\n"
    finally:
        if local_path.exists():
            local_path.unlink()
        manager.terminate(name=name)
