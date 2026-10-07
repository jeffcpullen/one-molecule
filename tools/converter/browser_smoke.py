"""Browser check: the staged page, run through Pyodide, matches the CPython projection.

Usage:
    python3 tools/converter/browser_smoke.py <staged-site-url> [--shots DIR]

Needs Playwright with Chromium. Exits non-zero on any mismatch. With `--shots`, saves
full-page PNGs of the collection-shared-state preset and of the roles preset at the
default of no limit and at workers 1.
"""

import argparse
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from cli import example_playbooks, example_scenarios_dir, example_source, load_schema, load_starter  # noqa: E402
from render import convert_text  # noqa: E402

READY_TIMEOUT_MS = 120000
VIEWPORT = {"width": 1366, "height": 900}
EDITOR = "#source .cm-content"
FILE_BUTTONS = "#tree button.file"
PROJECTED = "#tree button.file[data-kind=projected]"
SHOWN_PATHS = "[...document.querySelectorAll('#tree button.file[data-kind=projected]')].map(b => b.dataset.path)"
BLOCKS = ("[...document.querySelectorAll('#order svg g.block')]"
          ".map(g => [g.dataset.name, Number(g.dataset.step), g.getAttribute('transform')])")
SOURCE_NAME = "molecule.yml"


def shown_paths(page):
    """Return the full paths of the projected file buttons in the tree."""
    return page.evaluate(SHOWN_PATHS)


def buttons(page, selector):
    """Return [path, kind, available] for each file button under `selector`."""
    return page.evaluate(
        f"[...document.querySelectorAll('{selector} button.file')]"
        ".map(b => [b.dataset.path, b.dataset.kind, b.dataset.available !== 'false'])")


def blocks(page):
    """Return {name: (step, transform)} for the start order blocks."""
    return {name: (step, transform) for name, step, transform in page.evaluate(BLOCKS)}


def expected_steps(order):
    """Return {name: step} from a `start_steps` result."""
    return {s["name"]: s["step"] for s in order["scenarios"]}


def wait_for_steps(page, steps):
    """Wait until the start order blocks carry exactly `steps`."""
    want = json.dumps(sorted([n, s] for n, s in steps.items()), separators=(",", ":"))
    page.wait_for_function(
        f"JSON.stringify({BLOCKS}.map(b => [b[0], b[1]]).sort()) === {json.dumps(want)}")


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


def check_playbooks(page, slug, expected, present):
    """Both file columns list the referenced playbooks, open each one, and mark the missing ones."""
    source_buttons = buttons(page, "#source-files")
    want = [[SOURCE_NAME, "source", True]] + [[p, "playbook", p in present] for p in expected["playbooks"]]
    assert source_buttons == want, (slug, source_buttons)
    projected = [f["path"] for f in expected["files"]]
    tree = buttons(page, "#tree")
    want = [[p, "projected", True] for p in projected]
    want += [[p, "playbook", p in present] for p in expected["playbooks"] if p not in projected]
    assert tree == want, (slug, tree)
    source = page.evaluate("converter.source()")
    for path in expected["playbooks"]:
        page.click(f'#source-files button.file[data-path="{path}"]')
        assert page.text_content("#source-path") == path, (slug, path)
        assert page.is_hidden("#source"), (slug, path)
        if path in present:
            assert page.evaluate("converter.sourceFile()") == present[path], (slug, path)
            editable = page.get_attribute("#source-file .cm-content", "contenteditable")
            assert editable == "false", (slug, path, editable)
        else:
            assert page.is_visible("#source-missing"), (slug, path)
            assert "is not part of this input" in page.text_content("#source-missing"), (slug, path)
        page.click(f'#tree button.file[data-path="{path}"]')
        assert page.text_content("#file-path") == path, (slug, path)
        if path in present:
            assert page.evaluate("converter.file()") == present[path], (slug, path)
        else:
            assert page.is_visible("#file-missing"), (slug, path)
    page.click(f'#source-files button.file[data-path="{SOURCE_NAME}"]')
    assert page.is_visible("#source"), slug
    assert page.evaluate("converter.source()") == source, slug


def check_preset(page, slug, schema):
    """Load one preset in the page and compare every file, playbook, notice and start step with CPython."""
    scenarios_dir = example_scenarios_dir(slug)
    expected = convert_text(example_source(slug).read_text(), schema, scenarios_dir)
    present = example_playbooks(slug)
    page.select_option("#preset", slug)
    assert page.input_value("#scenarios-dir") == scenarios_dir, (slug, page.input_value("#scenarios-dir"))
    expected_paths = [f["path"] for f in expected["files"]]
    page.wait_for_function(f"{SHOWN_PATHS}.join() === {json.dumps(','.join(expected_paths))}")
    paths = shown_paths(page)
    assert paths == expected_paths, (slug, paths)
    for item in expected["files"]:
        page.click(f'{PROJECTED}[data-path="{item["path"]}"]')
        shown = page.evaluate("converter.file()")
        assert shown == item["text"], (slug, item["path"], shown)
        assert page.text_content("#file-path") == item["path"], (slug, item["path"])
        selected = page.locator(f"{FILE_BUTTONS}.selected").get_attribute("data-path")
        assert selected == item["path"], (slug, selected)
    shown_notices = page.locator("#notices li").all_text_contents()
    assert shown_notices == notice_lines(expected), (slug, shown_notices)
    check_playbooks(page, slug, expected, present)
    steps = expected_steps(expected["order"])
    shown_steps = {name: step for name, (step, _) in blocks(page).items()}
    assert shown_steps == steps, (slug, shown_steps)
    assert expected["order"]["workers"] is None, slug
    assert page.input_value("#workers") == "", (slug, page.input_value("#workers"))
    missing = sum(1 for p in expected["playbooks"] if p not in present)
    print(f"ok {slug}: {len(paths)} file(s), {len(expected['playbooks'])} playbook(s) ({missing} not available), "
          f"{len(expected['notices'])} notice(s), {len(steps)} start step(s) match CPython")


def check_layout(page):
    """Both file lists are vertical columns to the left of their code areas."""
    for listing, viewer in (("#source-files", "#source"), ("#tree", "#file")):
        column = page.locator(listing).bounding_box()
        code = page.locator(viewer).bounding_box()
        assert column["x"] + column["width"] <= code["x"], (listing, column, code)
        assert column["y"] <= code["y"], (listing, column, code)
        boxes = [b.bounding_box() for b in page.locator(f"{listing} button.file").all()]
        assert len(boxes) > 1, listing
        for upper, lower in zip(boxes, boxes[1:]):
            assert lower["y"] >= upper["y"] + upper["height"], (listing, upper, lower)
            assert lower["x"] < code["x"], (listing, lower)
    print("ok both file lists are vertical columns left of the code area")


def check_edit_survives(page):
    """An edit to molecule.yml survives viewing a referenced playbook."""
    page.select_option("#preset", "collection")
    page.wait_for_selector("#source-files button.file[data-kind=playbook]")
    text = page.evaluate("converter.source()") + "# edited\n"
    page.fill(EDITOR, text)
    first = page.locator("#source-files button.file[data-kind=playbook]").first
    first.click()
    assert page.is_hidden("#source")
    page.click(f'#source-files button.file[data-path="{SOURCE_NAME}"]')
    assert page.evaluate("converter.source()") == text, "the edit did not survive viewing a playbook"
    print("ok an edit to molecule.yml survives viewing a referenced playbook")


def check_workers(page, schema, shots):
    """Workers is empty and unlimited by default, a typed value caps at once, and clearing it restores no limit."""
    slug = "roles"
    text = example_source(slug).read_text()
    page.select_option("#preset", slug)
    default = expected_steps(convert_text(text, schema, "molecule")["order"])
    wait_for_steps(page, default)
    assert page.input_value("#workers") == "", page.input_value("#workers")
    assert page.get_attribute("#workers", "placeholder") == "no limit"
    assert set(default.values()) == {1}, default
    before = blocks(page)
    if shots:
        page.screenshot(path=str(shots / "roles-workers-default.png"), full_page=True)
    one = expected_steps(convert_text(text, schema, "molecule", 1)["order"])
    assert one != default, (one, default)
    page.fill("#workers", "1")
    page.wait_for_timeout(100)
    shown = {name: step for name, (step, _) in blocks(page).items()}
    assert shown == one, shown
    after = blocks(page)
    moved = [n for n in before if before[n][1] != after[n][1]]
    assert moved, (before, after)
    if shots:
        page.screenshot(path=str(shots / "roles-workers-1.png"), full_page=True)
    print(f"ok workers 1 redraws at once and moves {len(moved)} block(s): {one}")
    for bad in ("0", "-2", "1.5"):
        page.fill("#workers", bad)
        page.wait_for_timeout(100)
        assert page.evaluate("document.getElementById('workers').matches(':invalid')"), bad
        assert blocks(page) == after, (bad, blocks(page))
    page.locator("#workers").select_text()
    page.locator("#workers").press_sequentially("e")
    page.wait_for_timeout(100)
    assert page.evaluate("document.getElementById('workers').validity.badInput")
    assert page.evaluate("document.getElementById('workers').matches(':invalid')")
    assert blocks(page) == after, blocks(page)
    print("ok an invalid workers entry is marked invalid and keeps the last graphic")
    page.fill("#workers", "10")
    wait_for_steps(page, default)
    assert page.input_value("#workers") == "10", page.input_value("#workers")
    assert not page.evaluate("document.getElementById('workers').matches(':invalid')")
    print("ok workers above the scenario count stays as typed and binds nothing")
    page.fill("#workers", "1")
    wait_for_steps(page, one)
    page.fill("#workers", "")
    wait_for_steps(page, default)
    assert page.input_value("#workers") == ""
    assert not page.evaluate("document.getElementById('workers').matches(':invalid')")
    print("ok clearing workers restores no limit")
    page.fill("#workers", "2")
    wait_for_steps(page, expected_steps(convert_text(text, schema, "molecule", 2)["order"]))
    page.select_option("#preset", "collection")
    page.wait_for_function("document.getElementById('workers').value === ''")
    print("ok loading a preset clears workers")


def check_typed_missing(page, schema):
    """A playbook named in typed input is listed on both sides and marked not available."""
    page.click("#starter")
    text = ("---\nscenarios:\n  - name: typed\n    playbooks:\n"
            "      verify: ../../../playbooks/molecule/verify-typed.yml\n")
    page.fill(EDITOR, text)
    path = "playbooks/molecule/verify-typed.yml"
    assert convert_text(text, schema)["playbooks"] == [path]
    page.wait_for_selector(f'#tree button.file[data-path="{path}"]')
    for side, note in (("#source-files", "#source-missing"), ("#tree", "#file-missing")):
        button = page.locator(f'{side} button.file[data-path="{path}"]')
        assert button.get_attribute("data-available") == "false", side
        assert "missing" in button.get_attribute("class"), side
        assert "not available" in button.text_content(), side
        button.click()
        assert page.is_visible(note), side
        assert page.text_content(note) == f"{path} is not part of this input.", side
    page.click(f'#source-files button.file[data-path="{SOURCE_NAME}"]')
    assert page.evaluate("converter.source()") == text
    print("ok a playbook named in typed input is marked not available on both sides")


def check_starter(page, schema):
    """A fresh page opens on the starter file and shows its projection."""
    text = load_starter()
    assert page.evaluate("converter.source()") == text, "page did not open on the starter file"
    expected = convert_text(text, schema)
    page.wait_for_function(f"document.querySelectorAll('{PROJECTED}').length > 0")
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
    page.select_option("#scenarios-dir", "molecule")
    page.wait_for_function(f"{SHOWN_PATHS}.join() === 'molecule/shared-link/molecule.yml'")
    page.click("#share")
    page.wait_for_function("window.location.hash.includes('&dir=molecule')")
    third = context.new_page()
    third.goto(page.url)
    third.wait_for_selector("#status:has-text('Ready')", timeout=READY_TIMEOUT_MS)
    assert third.input_value("#scenarios-dir") == "molecule"
    assert shown_paths(third) == ["molecule/shared-link/molecule.yml"]
    print("ok the scenarios directory selector reruns the conversion and round-trips the share link")
    bad = context.new_page()
    bad.goto(third.url.replace("&dir=molecule", "&dir=..%2Fetc"))
    bad.wait_for_selector("#status:has-text('Ready')", timeout=READY_TIMEOUT_MS)
    assert bad.input_value("#scenarios-dir") == "extensions/molecule", bad.input_value("#scenarios-dir")
    assert shown_paths(bad) == ["extensions/molecule/shared-link/molecule.yml"], shown_paths(bad)
    print("ok a share link with an unknown scenarios directory keeps the default")
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


def main(url, shots=None):
    """Run every check against the staged site at `url`, saving screenshots under `shots` when given."""
    schema = load_schema()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
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
        page.select_option("#preset", "collection-shared-state")
        page.wait_for_selector("#order svg g.block[data-name=app_users]")
        check_layout(page)
        if shots:
            page.screenshot(path=str(shots / "collection-shared-state.png"), full_page=True)
        check_workers(page, schema, shots)
        check_edit_survives(page)
        check_typed_missing(page, schema)
        assert not errors, errors
        print("ok no uncaught page errors")
        check_share(browser, url)
        check_missing_module(browser, url)
        browser.close()
    if shots:
        print("screenshots in", shots)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("url")
    parser.add_argument("--shots", type=pathlib.Path)
    args = parser.parse_args()
    main(args.url, args.shots)
