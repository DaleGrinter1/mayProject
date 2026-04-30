from html.parser import HTMLParser
import sys
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from ssURL import screenshot_url


class DuckDuckGoResultsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result_urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag != "a" or "result__a" not in attrs.get("class", ""):
            return

        href = attrs.get("href")
        if href:
            self.result_urls.append(clean_result_url(href))


def clean_result_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    if "uddg" in query:
        return unquote(query["uddg"][0])

    return url


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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: uv run python searchSS.py <search terms>")

    query = " ".join(sys.argv[1:])
    url = first_search_result(query)
    print(f"First result: {url}")

    saved_path = screenshot_url(url)
    print(f"Screenshot saved to {saved_path.resolve()}")
