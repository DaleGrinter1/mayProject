# mayproject

Create a Modal sandbox that opens a URL with Playwright/Chromium and copies a
screenshot back into the local `screenshots/` folder.

## Usage

```bash
uv run python screenshot.py https://example.com
uv run python screenshot.py "example search term"
```

`screenshot.py` screenshots the input directly when it is a valid `http` or
`https` URL. Otherwise, it searches DuckDuckGo and screenshots the first result.

The first run may take longer while Modal builds the sandbox image.
