from agent_sandbox.sandbox import images


def test_get_image_supports_dev_image(monkeypatch) -> None:
    monkeypatch.setattr(images, "dev_image", lambda: "dev-image")

    assert images.get_image("dev") == "dev-image"
