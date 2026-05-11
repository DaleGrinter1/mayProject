from collections.abc import Callable, Sequence
from dataclasses import dataclass
import shutil
import subprocess
import sys

import modal

from mayproject.sandbox.types import ImageName


@dataclass(frozen=True)
class DoctorCheck:
    """Shows whether one setup check passed.

    Attributes:
        name: The setup item being checked.
        ok: Whether the check passed.
        message: A plain explanation for the result.
    """

    name: str
    ok: bool
    message: str


CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def run_doctor(
    command_runner: CommandRunner | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> list[DoctorCheck]:
    """Checks whether this computer is ready to use Modal.

    Args:
        command_runner: Optional command runner for tests.
        which: Optional command finder for tests.

    Returns:
        The setup checks and their results.
    """

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
    """Checks that the project Python version is active.

    Returns:
        The Python version check result.
    """

    if sys.version_info[:2] == (3, 13):
        return DoctorCheck("Python", True, "Python 3.13 is active.")
    version = ".".join(str(part) for part in sys.version_info[:3])
    return DoctorCheck("Python", False, f"Python {version} is active; use Python 3.13.")


def check_modal_sdk() -> DoctorCheck:
    """Checks that the Modal Python package is installed.

    Returns:
        The Modal package check result.
    """

    version = getattr(modal, "__version__", "unknown")
    return DoctorCheck("Modal SDK", True, f"Modal SDK {version} is installed.")


def check_modal_cli(which: Callable[[str], str | None]) -> DoctorCheck:
    """Checks that the Modal command is available.

    Args:
        which: A command finder.

    Returns:
        The Modal command check result.
    """

    path = which("modal")
    if path:
        return DoctorCheck("Modal CLI", True, f"Modal CLI found at {path}.")
    return DoctorCheck("Modal CLI", False, "Install or expose the Modal CLI on PATH.")


def check_modal_auth(command_runner: CommandRunner) -> DoctorCheck:
    """Checks that Modal has login details.

    Args:
        command_runner: Runs the Modal auth check command.

    Returns:
        The Modal login check result.
    """

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
    """Shows the remote computer images this project knows.

    Returns:
        The known images check result.
    """

    names: tuple[ImageName, ...] = ("python", "browser", "dev")
    return DoctorCheck("Images", True, "Available images: " + ", ".join(names) + ".")


def run_command(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Runs a local setup check command.

    Args:
        command: The command and its arguments.

    Returns:
        The local command result.
    """

    return subprocess.run(command, check=False, capture_output=True, text=True)
