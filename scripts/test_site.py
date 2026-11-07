#!/usr/bin/env python3
"""Run isolated browser smoke tests against the static site in site/."""

import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import Browser, Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "site"
RESULTS = ROOT / "test-results"
RELEASES = "https://github.com/VVG-web/cornetta-en/releases/latest"
WINDOWS_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
IPHONE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *args):
        pass


def launch(browser_type) -> Browser:
    override = os.environ.get("CORNETTA_CHROMIUM")
    if override:
        return browser_type.launch(executable_path=override, headless=True)
    candidates = [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return browser_type.launch(executable_path=str(candidate), headless=True)
    return browser_type.launch(headless=True)


def open_page(browser: Browser, base: str, path: str, *, user_agent: str | None = None,
              viewport: dict | None = None, mobile: bool = False) -> tuple:
    context = browser.new_context(
        user_agent=user_agent,
        viewport=viewport or {"width": 1440, "height": 1000},
        is_mobile=mobile,
        has_touch=mobile,
    )
    page = context.new_page()
    errors = []
    requests = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: requests.append(request.url))
    response = page.goto(base + path, wait_until="networkidle")
    assert response and response.status == 200, (path, response.status if response else None)
    assert not errors, errors
    return context, page, requests


def assert_no_horizontal_overflow(page: Page) -> None:
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), page.evaluate(
        "({width: innerWidth, scroll: document.documentElement.scrollWidth})"
    )


def assert_relative_internal_urls(page: Page) -> None:
    references = page.eval_on_selector_all(
        "[href], [src]",
        "elements => elements.map(element => element.getAttribute('href') || element.getAttribute('src'))",
    )
    absolute = [reference for reference in references if reference and reference.startswith("/")]
    assert not absolute, absolute


def capture(page: Page, name: str) -> None:
    page.locator("img[loading='lazy']").evaluate_all("images => images.forEach(image => image.loading = 'eager')")
    page.wait_for_function("Array.from(document.images).every(image => image.complete)")
    broken = page.locator("img").evaluate_all("images => images.filter(image => !image.naturalWidth).map(image => image.src)")
    assert not broken, broken
    page.evaluate("window.scrollTo(0, 0)")
    page.screenshot(path=RESULTS / name, full_page=True)


def assert_no_analytics(page: Page, requests: list[str]) -> None:
    assert page.locator("script[data-domain]").count() == 0
    assert page.locator("script[data-api]").count() == 0
    assert page.locator('script[src^="http"]').count() == 0
    assert not [url for url in requests if "/api/" in url or "plausible" in url or "telegram" in url], requests


def run(base: str, browser: Browser) -> None:
    RESULTS.mkdir(exist_ok=True)

    context, page, requests = open_page(browser, base, "/en/")
    assert "Cornetta" in page.title()
    assert page.locator("html").get_attribute("lang") == "en"
    assert page.locator("h1").is_visible()
    assert page.locator("[data-download-primary]").first.get_attribute("href") == RELEASES
    assert_no_analytics(page, requests)
    assert_relative_internal_urls(page)
    faq = page.locator("details").first
    faq.locator("summary").click()
    assert faq.get_attribute("open") is not None
    assert_no_horizontal_overflow(page)
    capture(page, "site-en-desktop.png")
    context.close()
    print("PASS English desktop, GitHub download, FAQ, no analytics, layout")

    context, page, requests = open_page(browser, base, "/en/", user_agent=WINDOWS_UA)
    assert "PC." in page.locator("h1").inner_text()
    assert page.locator("[data-os='windows']").first.is_visible()
    assert page.locator("[data-download-primary]").first.get_attribute("href") == RELEASES
    assert_no_analytics(page, requests)
    assert_relative_internal_urls(page)
    context.close()
    print("PASS Windows copy and GitHub download")

    context, page, requests = open_page(browser, base, "/en/privacy/")
    assert "No telemetry" in page.locator("h1").inner_text()
    assert page.get_by_text("GitHub", exact=False).first.is_visible()
    assert page.locator("script[src^='http']").count() == 0
    assert_no_analytics(page, requests)
    assert_relative_internal_urls(page)
    capture(page, "site-en-privacy.png")
    context.close()
    print("PASS English privacy page")

    context, page, requests = open_page(
        browser, base, "/en/", user_agent=IPHONE_UA, viewport={"width": 390, "height": 844}, mobile=True
    )
    assert_no_horizontal_overflow(page)
    assert_no_analytics(page, requests)
    assert_relative_internal_urls(page)
    capture(page, "site-en-mobile.png")
    context.close()
    print("PASS mobile layout")

    context, page, requests = open_page(browser, base, "/")
    assert page.locator("html").get_attribute("lang") == "it"
    assert "Cornetta" in page.title()
    assert page.locator("[data-download-primary]").first.get_attribute("href") == RELEASES
    assert_no_analytics(page, requests)
    assert_relative_internal_urls(page)
    context.close()
    print("PASS Italian homepage")


def main() -> None:
    handler = partial(QuietHandler, directory=str(PUBLIC))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with sync_playwright() as playwright:
            try:
                browser = launch(playwright.chromium)
            except Exception as error:
                raise RuntimeError(
                    "No usable Chromium. Install Google Chrome or run "
                    "'.venv/bin/python -m playwright install chromium --no-remove'."
                ) from error
            try:
                run(base, browser)
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
