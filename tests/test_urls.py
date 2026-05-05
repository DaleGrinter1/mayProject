from mayproject.urls import is_valid_url

# Test for if the URL validation function correctly identifies valid URLs
def test_is_valid_url_accepts_http_and_https() -> None:
    assert is_valid_url("https://example.com")
    assert is_valid_url("http://example.com/path")

# Test for if the URL validation function correctly identifies invalid URLs
def test_is_valid_url_rejects_search_terms_and_unsupported_schemes() -> None:
    assert not is_valid_url("example search")
    assert not is_valid_url("ftp://example.com")
    assert not is_valid_url("https://")

