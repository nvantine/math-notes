"""Real Chromium checks for keyboard disclosures, fragments, layout, and previews."""
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
from playwright.sync_api import expect, sync_playwright


@pytest.fixture(scope="module")
def site_url(built_site):
    handler = partial(SimpleHTTPRequestHandler, directory=str(built_site))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    worker.join()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_independent_disclosures_work_with_keyboard(browser, site_url, theme):
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{site_url}/linear-algebra/vector-spaces.html")
        if theme == "dark":
            page.get_by_title("Toggle dark mode").click()
        exercise = page.locator("#exr-double-negation")
        solution = exercise.locator(":scope > .callout-tip .callout-header")
        lean = page.locator("#lean-double-negation .callout-header")
        expect(solution).to_have_attribute("aria-expanded", "false")
        expect(lean).to_have_attribute("aria-expanded", "false")
        solution.focus()
        page.keyboard.press("Enter")
        expect(solution).to_have_attribute("aria-expanded", "true")
        expect(lean).to_have_attribute("aria-expanded", "false")
        lean.focus()
        page.keyboard.press("Space")
        expect(lean).to_have_attribute("aria-expanded", "true")
        expect(exercise.locator("pre.lean4")).to_be_visible()
        keyword = exercise.locator("pre.lean4 .kn").first
        assert keyword.evaluate("el => getComputedStyle(el).color") != exercise.locator("pre.lean4 .n").first.evaluate("el => getComputedStyle(el).color")
        expect(exercise.get_by_role("link", name="Open in Lean playground")).to_have_attribute("href", re.compile(r"https://live\.lean-lang\.org/#codez="))
        proof = page.locator("#thm-zero-times-vector > .callout-tip .callout-header")
        expect(proof).to_have_attribute("aria-expanded", "false")
        proof.focus()
        page.keyboard.press("Enter")
        expect(proof).to_have_attribute("aria-expanded", "true")
        assert not errors
    finally:
        page.close()


@pytest.mark.parametrize("width", [390, 1440])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_pages_fit_mobile_and_desktop(browser, site_url, width, theme):
    page = browser.new_page(viewport={"width": width, "height": 900})
    try:
        for path in ("", "linear-algebra/vector-spaces.html", "convex-optimization/convex-sets.html"):
            page.goto(f"{site_url}/{path}")
            if theme == "dark" and "quarto-dark" not in page.locator("body").get_attribute("class"):
                page.get_by_title("Toggle dark mode").click()
            for toggle in page.locator('.callout-header[data-bs-toggle="collapse"]').all():
                toggle.click()
                expect(toggle).to_have_attribute("aria-expanded", "true")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (path, width, theme)
    finally:
        page.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_cross_chapter_preview_typesets_math(browser, site_url, theme):
    page = browser.new_page()
    try:
        page.goto(f"{site_url}/linear-algebra/index.html")
        if theme == "dark":
            page.get_by_title("Toggle dark mode").click()
        page.locator('a.quarto-xref[href$="#exr-double-negation"]').hover()
        preview = page.locator(".tippy-content").last
        expect(preview.locator("mjx-container").first).to_be_visible(timeout=30000)
        assert preview.locator(".math:not(:has(mjx-container))").count() == 0
    finally:
        page.close()


def test_lean_fragment_opens_only_its_disclosure(browser, site_url):
    page = browser.new_page()
    try:
        page.goto(f"{site_url}/linear-algebra/vector-spaces.html#lean-double-negation")
        expect(page.locator("#lean-double-negation .callout-collapse")).to_be_visible()
        expect(page.locator("#lean-zero-times-vector .callout-collapse")).to_be_hidden()
        expect(page.locator("#exr-double-negation > .callout-tip .callout-collapse")).to_be_hidden()
        page.evaluate("location.hash = 'lean-add-inv-swap'")
        expect(page.locator("#lean-add-inv-swap .callout-collapse")).to_be_visible()
    finally:
        page.close()
