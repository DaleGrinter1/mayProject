from urllib.parse import urlparse


def is_valid_url(text: str) -> bool:
    """Checks whether text is a normal web address.

    Args:
        text: The text to check.

    Returns:
        True when the text is an http or https web address.
    """

    parsed = urlparse(text)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)
