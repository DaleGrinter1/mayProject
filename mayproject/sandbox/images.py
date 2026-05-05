import modal

from mayproject.sandbox.types import ImageName


def python_image() -> modal.Image:
    return modal.Image.debian_slim(python_version="3.13")


def browser_image() -> modal.Image:
    return (
        python_image()
        .pip_install("playwright")
        .run_commands("python -m playwright install --with-deps chromium")
    )


def get_image(name: ImageName) -> modal.Image:
    image_builders = {
        "python": python_image,
        "browser": browser_image,
    }
    return image_builders[name]()
