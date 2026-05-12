"""Tests for URL validation before screenshot/search resolution."""

from agent_sandbox.urls import is_valid_url


def test_is_valid_url_accepts_http_and_https() -> None:
    """Verify web URLs are accepted as direct screenshot targets."""

    assert is_valid_url("https://example.com")
    assert is_valid_url("http://example.com/path")


def test_is_valid_url_rejects_search_terms_and_unsupported_schemes() -> None:
    """Verify search terms and unsupported schemes are not treated as URLs."""

    assert not is_valid_url("example search")
    assert not is_valid_url("ftp://example.com")
    assert not is_valid_url("https://")
