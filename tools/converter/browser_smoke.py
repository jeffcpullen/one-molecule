"""Browser check: the staged page, run through Pyodide, matches the CPython projection.

Usage:
    python3 tools/converter/browser_smoke.py <staged-site-url>

Needs Playwright with Chromium. Exits non-zero on any mismatch.
"""

import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from cli import ROOT, load_schema, load_starter  # noqa: E402
from render import convert_text  # noqa: E402

READY_TIMEOUT_MS = 120000
EDITOR = "#source .cm-content"
FILE_BUTTONS = "#tree button.file"
SHOWN_PATHS = "[...document.querySelectorAll('#tree button.file')].map(b => b.dataset.path)"


def shown_paths(page):
    """Return the full paths of the file buttons in the tree."""
    return page.evaluate(SHOWN_PATHS)


def notice_lines(result):
    """Render notices the way the page lists them.

    Args:
        result: a `convert_text` result.

    Returns:
        The list of notice strings.
    """
    lines = []
    for n in result["notices"]:
        where = " / ".join(x for x in (n["node"], n["key"]) if x)
        lines.append(f"{n['kind']}{' (' + where + ')' if where else ''}: {n['message']}")
    return lines or ["None."]


def check_preset(page, slug, schema):
    """Load one preset in the page and compare every file and notice with CPython."""
    expected = convert_text((ROOT / "examples" / slug / "after" / "molecule.yml").read_text(), schema)
    page.select_option("#preset", slug)
    expected_paths = [f["path"] for f in expected["files"]]
    page.wait_for_function(f"{SHOWN_PATHS}.join() === {json.dumps(','.join(expected_paths))}")
    paths = shown_paths(page)
    assert paths == expected_paths, (slug, paths)
    for item in expected["files"]:
        page.click(f'{FILE_BUTTONS}[data-path="{item["path"]}"]')
        shown = page.evaluate("converter.file()")
        assert shown == item["text"], (slug, item["path"], shown)
        assert page.text_content("#file-path") == item["path"], (slug, item["path"])
        selected = page.locator(f"{FILE_BUTTONS}.selected").get_attribute("data-path")
        assert selected == item["path"], (slug, selected)
    shown_notices = page.locator("#notices li").all_text_contents()
    assert shown_notices == notice_lines(expected), (slug, shown_notices)
    print(f"ok {slug}: {len(paths)} file(s), {len(expected['notices'])} notice(s) match CPython")


def check_starter(page, schema):
    """A fresh page opens on the starter file and shows its projection."""
    text = load_starter()
    assert page.evaluate("converter.source()") == text, "page did not open on the starter file"
    expected = convert_text(text, schema)
    page.wait_for_function(f"document.querySelectorAll('{FILE_BUTTONS}').length > 0")
    paths = shown_paths(page)
    assert paths == [f["path"] for f in expected["files"]], paths
    page.select_option("#preset", "")
    page.fill(EDITOR, "")
    page.click("#starter")
    assert page.evaluate("converter.source()") == text, "the Starter button did not restore the starter file"
    print(f"ok the page opens on the starter file: {len(paths)} file(s)")


def check_share(browser, url):
    """Round-trip the editor text through the share link."""
    context = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
    page = context.new_page()
    page.goto(url)
    page.wait_for_selector("#status:has-text('Ready')", timeout=READY_TIMEOUT_MS)
    text = "---\nscenarios:\n  - name: shared-link\n"
    page.fill(EDITOR, text)
    assert page.evaluate("converter.source()") == text, "the editor changed the typed text"
    page.wait_for_function(f"{SHOWN_PATHS}.join() === 'extensions/molecule/shared-link/molecule.yml'")
    print("ok typing in the editor reruns the conversion")
    page.click("#share")
    page.wait_for_function("window.location.hash.startsWith('#src=')")
    link = page.url
    other = context.new_page()
    other.goto(link)
    other.wait_for_selector("#status:has-text('Ready')", timeout=READY_TIMEOUT_MS)
    assert other.evaluate("converter.source()") == text
    assert shown_paths(other) == ["extensions/molecule/shared-link/molecule.yml"]
    print("ok share link round-trips the source")
    context.close()


def check_missing_module(browser, url):
    """A module that fails to load names itself and its HTTP status in the page status."""
    context = browser.new_context()
    page = context.new_page()
    requested = []
    page.on("request", lambda r: requested.append(r.url))
    page.route("**/project.py*", lambda route: route.fulfill(status=404, body="not found"))
    page.goto(url)
    page.wait_for_selector("#status:has-text('Failed to start')", timeout=READY_TIMEOUT_MS)
    status = page.text_content("#status")
    assert "could not load project.py (HTTP 404)" in status, status
    assert any("project.py?v=" in r for r in requested), requested
    print("ok a missing module is reported by name and status")
    context.close()


def main(url):
    """Run every check against the staged site at `url`."""
    schema = load_schema()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector("#status:has-text('Ready')", timeout=READY_TIMEOUT_MS)
        print("status:", page.text_content("#status"))
        shown_version = page.text_content("#spec-version")
        assert shown_version == schema["x-spec"]["version"], shown_version
        print(f"ok the page names spec {shown_version}")
        check_starter(page, schema)
        slugs = page.locator("#preset option").evaluate_all("o => o.map(x => x.value).filter(v => v)")
        assert slugs, "no presets"
        for slug in slugs:
            check_preset(page, slug, schema)
        check_share(browser, url)
        check_missing_module(browser, url)
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1])
