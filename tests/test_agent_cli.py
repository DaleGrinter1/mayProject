import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from mayproject.cli.agent import main, parse_inputs


TEST_TMP_ROOT = Path("artifacts") / "test-agent-cli"


def workspace_temp_dir() -> Path:
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = TEST_TMP_ROOT / uuid4().hex
    path.mkdir()
    return path


def test_agent_list_prints_builtin_agents(capsys: pytest.CaptureFixture[str]) -> None:
    result = main(["list"])

    output = capsys.readouterr().out
    assert result == 0
    assert "Agent" in output
    assert "echo" in output
    assert "Echo" in output


def test_agent_list_prints_json(capsys: pytest.CaptureFixture[str]) -> None:
    result = main(["list", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload[0]["agent_id"] == "echo"
    assert payload[0]["role"] == "Echo"


def test_agent_run_executes_selected_agent(capsys: pytest.CaptureFixture[str]) -> None:
    run_root = workspace_temp_dir()
    try:
        result = main(
            [
                "run",
                "--agent",
                "echo",
                "--input",
                "audience=agent-authors",
                "--run-root",
                str(run_root),
                "Package",
                "the",
                "agent",
                "API",
            ]
        )

        output = capsys.readouterr().out
        assert result == 0
        assert "Workflow succeeded" in output
        assert "echo" in output
        echo_files = list(run_root.glob("*/agents/echo/echo.json"))
        assert len(echo_files) == 1
        payload = json.loads(echo_files[0].read_text(encoding="utf-8"))
        assert payload["objective"] == "Package the agent API"
        assert payload["inputs"] == {"audience": "agent-authors"}
    finally:
        shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)


def test_agent_run_prints_json(capsys: pytest.CaptureFixture[str]) -> None:
    run_root = workspace_temp_dir()
    try:
        result = main(["run", "--run-root", str(run_root), "--json", "Do", "work"])

        payload = json.loads(capsys.readouterr().out)
        assert result == 0
        assert payload["status"] == "succeeded"
        assert payload["task"]["objective"] == "Do work"
        assert payload["agent_runs"][0]["agent"]["agent_id"] == "echo"
    finally:
        shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)


def test_parse_inputs_rejects_values_without_equals() -> None:
    with pytest.raises(ValueError, match="key=value"):
        parse_inputs(["audience"])
