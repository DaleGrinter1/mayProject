import modal

from mayproject.sandbox.types import ImageName


def python_image() -> modal.Image:
    """Builds a small remote computer with Python.

    Returns:
        A Modal image with Python installed.
    """

    return modal.Image.debian_slim(python_version="3.13")


def browser_image() -> modal.Image:
    """Builds a remote computer that can open web pages.

    Returns:
        A Modal image with Playwright and Chromium installed.
    """

    return (
        python_image()
        .pip_install("playwright")
        .run_commands("python -m playwright install --with-deps chromium")
    )


def dev_image() -> modal.Image:
    """Builds a remote computer with everyday coding tools.

    Returns:
        A Modal image with Python, git, curl, bash, and uv.
    """

    return (
        python_image()
        .apt_install("bash", "curl", "git")
        .pip_install("uv")
    )


def get_image(name: ImageName) -> modal.Image:
    """Chooses the remote computer image by name.

    Args:
        name: The image name to choose.

    Returns:
        The Modal image for that name.
    """

    image_builders = {
        "python": python_image,
        "browser": browser_image,
        "dev": dev_image,
    }
    return image_builders[name]()
