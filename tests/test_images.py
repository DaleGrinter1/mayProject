"""Tests for selecting predefined Modal sandbox images."""

from agent_sandbox.sandbox import images


def test_get_image_supports_dev_image(monkeypatch) -> None:
    """Verify the image registry can resolve the developer image option."""

    monkeypatch.setattr(images, "dev_image", lambda: "dev-image")

    assert images.get_image("dev") == "dev-image"
