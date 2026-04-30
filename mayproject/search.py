from html.parser import HTMLParser
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen


class DuckDuckGoResultsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.result_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_by_name = dict(attrs)
        if tag != "a" or "result__a" not in (attrs_by_name.get("class") or ""):
            return

        href = attrs_by_name.get("href")
        if href:
            self.result_urls.append(clean_result_url(href))


def clean_result_url(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    return unquote(query["uddg"][0]) if "uddg" in query else url


def first_search_result(query: str) -> str:
    search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    request = Request(search_url, headers={"User-Agent": "Mozilla/5.0"})

    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")

    parser = DuckDuckGoResultsParser()
    parser.feed(html)

    if not parser.result_urls:
        raise RuntimeError(f"No search results found for: {query}")

    return parser.result_urls[0]

