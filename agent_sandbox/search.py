from html.parser import HTMLParser
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen


class DuckDuckGoResultsParser(HTMLParser):
    """Finds result links in DuckDuckGo's simple search page."""

    def __init__(self) -> None:
        # Store the result links found while reading the page.
        super().__init__()
        self.result_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collects links that look like search results.

        Args:
            tag: The HTML tag name.
            attrs: The HTML tag attributes.
        """

        attrs_by_name = dict(attrs)
        if tag != "a" or "result__a" not in (attrs_by_name.get("class") or ""):
            return

        href = attrs_by_name.get("href")
        if href:
            self.result_urls.append(clean_result_url(href))


def clean_result_url(url: str) -> str:
    """Turns a DuckDuckGo redirect into the real web address.

    Args:
        url: The result link from DuckDuckGo.

    Returns:
        The real web address when it can be found.
    """

    query = parse_qs(urlparse(url).query)
    return unquote(query["uddg"][0]) if "uddg" in query else url


def first_search_result(query: str) -> str:
    """Searches the web and returns the first result.

    Args:
        query: The search words.

    Returns:
        The first result web address.
    """

    search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    request = Request(search_url, headers={"User-Agent": "Mozilla/5.0"})

    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")

    parser = DuckDuckGoResultsParser()
    parser.feed(html)

    if not parser.result_urls:
        raise RuntimeError(f"No search results found for: {query}")

    return parser.result_urls[0]
