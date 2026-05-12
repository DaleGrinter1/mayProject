"""Tests for turning DuckDuckGo search result markup into usable URLs."""

from agent_sandbox.search import DuckDuckGoResultsParser, clean_result_url


def test_clean_result_url_extracts_duckduckgo_redirect() -> None:
    """Verify DuckDuckGo redirect links are decoded to their target URL."""

    url = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fdocs"

    assert clean_result_url(url) == "https://example.com/docs"


def test_duckduckgo_parser_collects_result_urls() -> None:
    """Verify the parser keeps result links and ignores unrelated anchors."""

    parser = DuckDuckGoResultsParser()

    parser.feed(
        """
        <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com">Example</a>
        <a class="other" href="https://ignored.example">Ignored</a>
        """
    )

    assert parser.result_urls == ["https://example.com"]
