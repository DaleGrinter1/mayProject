import subprocess

from agent_sandbox.workflows.doctor import check_modal_auth, run_doctor


def test_run_doctor_reports_ready_checks() -> None:
    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, "ok", "")

    checks = run_doctor(command_runner=runner, which=lambda name: "/bin/modal")

    assert {check.name for check in checks} == {
        "Python",
        "Modal SDK",
        "Modal CLI",
        "Modal auth",
        "Images",
    }
    assert all(check.ok for check in checks)


def test_run_doctor_reports_missing_modal_cli() -> None:
    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError

    checks = run_doctor(command_runner=runner, which=lambda name: None)
    by_name = {check.name: check for check in checks}

    assert not by_name["Modal CLI"].ok
    assert not by_name["Modal auth"].ok


def test_check_modal_auth_shows_command_error() -> None:
    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, "", "not logged in")

    check = check_modal_auth(runner)

    assert not check.ok
    assert check.message == "not logged in"
