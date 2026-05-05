from collections.abc import Callable, Sequence
from dataclasses import dataclass
import shutil
import subprocess
import sys

import modal

from mayproject.sandbox.types import ImageName


@dataclass(frozen=True)
class DoctorCheck:
    """Shows whether one setup check passed."""

    name: str
    ok: bool
    message: str


CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def run_doctor(
    command_runner: CommandRunner | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> list[DoctorCheck]:
    """Checks whether this computer is ready to use Modal."""

    runner = command_runner or run_command
    checks = [
        check_python_version(),
        check_modal_sdk(),
        check_modal_cli(which),
        check_modal_auth(runner),
        check_images(),
    ]
    return checks


def check_python_version() -> DoctorCheck:
    if sys.version_info[:2] == (3, 13):
        return DoctorCheck("Python", True, "Python 3.13 is active.")
    version = ".".join(str(part) for part in sys.version_info[:3])
    return DoctorCheck("Python", False, f"Python {version} is active; use Python 3.13.")


def check_modal_sdk() -> DoctorCheck:
    version = getattr(modal, "__version__", "unknown")
    return DoctorCheck("Modal SDK", True, f"Modal SDK {version} is installed.")


def check_modal_cli(which: Callable[[str], str | None]) -> DoctorCheck:
    path = which("modal")
    if path:
        return DoctorCheck("Modal CLI", True, f"Modal CLI found at {path}.")
    return DoctorCheck("Modal CLI", False, "Install or expose the Modal CLI on PATH.")


def check_modal_auth(command_runner: CommandRunner) -> DoctorCheck:
    try:
        result = command_runner(["modal", "token", "info"])
    except FileNotFoundError:
        return DoctorCheck("Modal auth", False, "Modal CLI was not found.")

    if result.returncode == 0:
        return DoctorCheck("Modal auth", True, "Modal has an active token.")
    detail = (result.stderr or result.stdout).strip()
    if detail:
        return DoctorCheck("Modal auth", False, detail)
    return DoctorCheck("Modal auth", False, "Run `uv run modal token new` to log in.")


def check_images() -> DoctorCheck:
    names: tuple[ImageName, ...] = ("python", "browser", "dev")
    return DoctorCheck("Images", True, "Available images: " + ", ".join(names) + ".")


def run_command(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)
