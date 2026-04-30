import sys

from playwright.sync_api import sync_playwright


url = sys.argv[1]
image_path = sys.argv[2]
text_path = sys.argv[3]


def lines_for_items(items):
    lines = []
    for item in items[:50]:
        text = " ".join((item.get("text") or "").split())
        href = item.get("href")
        if text and href:
            lines.append(f"- {text}: {href}")
        elif text:
            lines.append(f"- {text}")
    return lines or ["(none)"]


with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(2_000)

    links = page.eval_on_selector_all(
        "a",
        "els => els.map(el => ({ text: el.innerText, href: el.href })).filter(x => x.text || x.href)",
    )
    buttons = page.eval_on_selector_all(
        "button, input[type=button], input[type=submit]",
        "els => els.map(el => ({ text: el.innerText || el.value || el.getAttribute('aria-label') || '' }))",
    )
    visible_text = page.locator("body").inner_text(timeout=5_000)

    observation = [
        f"URL: {page.url}",
        f"Title: {page.title()}",
        "",
        "Visible text:",
        visible_text[:8000],
        "",
        "Links:",
        *lines_for_items(links),
        "",
        "Buttons:",
        *lines_for_items(buttons),
        "",
    ]

    page.screenshot(path=image_path, full_page=True)
    with open(text_path, "w", encoding="utf-8") as file:
        file.write("\n".join(observation))
    browser.close()

