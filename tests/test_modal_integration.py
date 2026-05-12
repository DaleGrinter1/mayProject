"""Opt-in integration tests that create real Modal sandboxes."""

import os
from pathlib import Path
from uuid import uuid4

import pytest

from agent_sandbox.workflows.sandbox import ManagedSandbox


ARTIFACTS_DIR = Path("artifacts")

# These tests are intentionally skipped by default because they create real
# remote resources and require a configured Modal account.
pytestmark = pytest.mark.skipif(
    os.environ.get("AGENT_SANDBOX_RUN_MODAL_TESTS") != "1",
    reason="set AGENT_SANDBOX_RUN_MODAL_TESTS=1 to run real Modal integration tests",
)


def test_modal_sandbox_can_copy_remote_text_file_to_local() -> None:
    """Create a real Modal sandbox and copy a text file back locally."""

    name = f"copy-test-{uuid4().hex[:8]}"
    remote_path = "/tmp/agent_sandbox-copy-test.txt"
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


def test_modal_sandbox_can_copy_local_script_and_execute_it() -> None:
    """Copy a local script into a real Modal sandbox and run it."""

    name = f"put-test-{uuid4().hex[:8]}"
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    local_script = ARTIFACTS_DIR / f"{name}.py"
    remote_script = "/tmp/agent_sandbox-put-test.py"
    manager = ManagedSandbox()

    try:
        local_script.write_text("print('hello from copied script')\n", encoding="utf-8")
        manager.create(name=name, image_name="python", timeout=300, idle_timeout=60)
        manager.copy_to(local_script, remote_script, name=name)
        result = manager.exec(["python", remote_script], name=name)

        assert result.returncode == 0
        assert result.stdout.strip() == "hello from copied script"
    finally:
        if local_script.exists():
            local_script.unlink()
        manager.terminate(name=name)
