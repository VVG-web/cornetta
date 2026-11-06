#!/usr/bin/env python3
"""Run isolated browser smoke tests against worker/public."""

import json
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse

from playwright.sync_api import Browser, Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "worker" / "public"
RESULTS = ROOT / "test-results"
LATEST = {
    "mac": {"version": "0.0.0-test", "size": 1_048_576, "sha256": "a" * 64, "url": "/download"},
    "windows": {"version": "0.0.0-test", "size": 2_097_152, "sha256": "b" * 64, "url": "/download/windows"},
}
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


def install_routes(page: Page, host: str) -> None:
    def route_request(route) -> None:
        url = route.request.url
        path = urlparse(url).path
        if urlparse(url).netloc != host:
            route.abort()
        elif path == "/downloads/latest.json":
            route.fulfill(status=200, content_type="application/json", body=json.dumps(LATEST))
        elif path == "/js/p.js":
            route.fulfill(status=200, content_type="application/javascript", body="")
        elif path == "/api/e":
            route.fulfill(status=202, body="")
        else:
            route.continue_()

    page.route("**/*", route_request)


def open_page(browser: Browser, base: str, path: str, *, user_agent: str | None = None,
              viewport: dict | None = None, mobile: bool = False) -> tuple:
    context = browser.new_context(
        user_agent=user_agent,
        viewport=viewport or {"width": 1440, "height": 1000},
        is_mobile=mobile,
        has_touch=mobile,
    )
    page = context.new_page()
    install_routes(page, urlparse(base).netloc)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    response = page.goto(base + path, wait_until="networkidle")
    assert response and response.status == 200, (path, response.status if response else None)
    assert not errors, errors
    return context, page


def assert_no_horizontal_overflow(page: Page) -> None:
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), page.evaluate(
        "({width: innerWidth, scroll: document.documentElement.scrollWidth})"
    )


def capture(page: Page, name: str) -> None:
    page.locator("img[loading='lazy']").evaluate_all("images => images.forEach(image => image.loading = 'eager')")
    page.wait_for_function("Array.from(document.images).every(image => image.complete)")
    broken = page.locator("img").evaluate_all("images => images.filter(image => !image.naturalWidth).map(image => image.src)")
    assert not broken, broken
    page.evaluate("window.scrollTo(0, 0)")
    page.screenshot(path=RESULTS / name, full_page=True)


def run(base: str, browser: Browser) -> None:
    RESULTS.mkdir(exist_ok=True)

    context, page = open_page(browser, base, "/en/")
    assert "Cornetta" in page.title()
    assert page.locator("html").get_attribute("lang") == "en"
    assert page.locator("h1").is_visible()
    assert "Version 0.0.0-test" in page.locator('[data-meta="mac"]').first.inner_text()
    checksum = page.locator('[data-sha="mac"]').first.text_content()
    assert checksum == "a" * 64, repr(checksum)
    faq = page.locator("details").first
    faq.locator("summary").click()
    assert faq.get_attribute("open") is not None
    assert_no_horizontal_overflow(page)
    capture(page, "site-en-desktop.png")
    context.close()
    print("PASS English desktop, release metadata, FAQ, layout")

    context, page = open_page(browser, base, "/en/", user_agent=WINDOWS_UA)
    assert "PC." in page.locator("h1").inner_text()
    assert page.locator("[data-download-primary]").first.get_attribute("href") == "/download/windows"
    context.close()
    print("PASS Windows download selection")

    context, page = open_page(
        browser, base, "/en/", user_agent=IPHONE_UA, viewport={"width": 390, "height": 844}, mobile=True
    )
    note = page.locator("#os-note")
    assert note.is_visible()
    assert "open this page on your Mac or PC" in note.inner_text()
    copy = note.get_by_role("button", name="Copy link")
    copy.click()
    page.wait_for_function(
        """() => { const note = document.querySelector('#os-note');
        return note.innerText.includes('Link copied') || note.querySelector('.os-link'); }"""
    )
    assert "Link copied" in note.inner_text() or note.locator(".os-link").is_visible()
    assert_no_horizontal_overflow(page)
    capture(page, "site-en-mobile.png")
    context.close()
    print("PASS mobile guidance, copy fallback, layout")

    context, page = open_page(browser, base, "/")
    assert page.locator("html").get_attribute("lang") == "it"
    assert "Cornetta" in page.title()
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
