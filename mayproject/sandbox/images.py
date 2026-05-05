import modal

from mayproject.sandbox.types import ImageName


def python_image() -> modal.Image:
    """Builds a small remote computer with Python."""

    return modal.Image.debian_slim(python_version="3.13")


def browser_image() -> modal.Image:
    """Builds a remote computer that can open web pages."""

    return (
        python_image()
        .pip_install("playwright")
        .run_commands("python -m playwright install --with-deps chromium")
    )


def dev_image() -> modal.Image:
    """Builds a remote computer with everyday coding tools."""

    return (
        python_image()
        .apt_install("bash", "curl", "git")
        .pip_install("uv")
    )


def get_image(name: ImageName) -> modal.Image:
    """Chooses the remote computer image by name."""

    image_builders = {
        "python": python_image,
        "browser": browser_image,
        "dev": dev_image,
    }
    return image_builders[name]()
