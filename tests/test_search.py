from mayproject.search import DuckDuckGoResultsParser, clean_result_url


def test_clean_result_url_extracts_duckduckgo_redirect() -> None:
    url = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fdocs"

    assert clean_result_url(url) == "https://example.com/docs"


def test_duckduckgo_parser_collects_result_urls() -> None:
    parser = DuckDuckGoResultsParser()

    parser.feed(
        """
        <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com">Example</a>
        <a class="other" href="https://ignored.example">Ignored</a>
        """
    )

    assert parser.result_urls == ["https://example.com"]

