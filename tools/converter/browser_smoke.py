"""Browser check: the staged page, run through Pyodide, matches the CPython projection.

Usage:
    python3 tools/converter/browser_smoke.py <staged-site-url> [--shots DIR]

Needs Playwright with Chromium. Exits non-zero on any mismatch. With `--shots`, saves
full-page PNGs of the collection-shared-state preset and of the roles preset at the
default of 1 worker and at workers 3.
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


def check_shared(page, slug, expected, present):
    """Only the shared pane lists the referenced playbooks, once each, opens each one and marks the missing ones."""
    source_buttons = buttons(page, "#source-files")
    assert source_buttons == [[SOURCE_NAME, "source", True]], (slug, source_buttons)
    tree = buttons(page, "#tree")
    assert tree == [[f["path"], "projected", True] for f in expected["files"]], (slug, tree)
    shared = buttons(page, "#shared-files")
    assert shared == [[p, "playbook", p in present] for p in expected["playbooks"]], (slug, shared)
    assert len({p for p, _, _ in shared}) == len(shared), (slug, shared)
    assert page.is_hidden("#shared-empty"), slug
    source = page.evaluate("converter.source()")
    for path in expected["playbooks"]:
        page.click(f'#shared-files button.file[data-path="{path}"]')
        assert page.text_content("#shared-path") == path, (slug, path)
        if path in present:
            assert page.evaluate("converter.sharedFile()") == present[path], (slug, path)
            editable = page.get_attribute("#shared-file .cm-content", "contenteditable")
            assert editable == "false", (slug, path, editable)
        else:
            assert page.is_visible("#shared-missing"), (slug, path)
            assert "is not part of this input" in page.text_content("#shared-missing"), (slug, path)
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
    check_shared(page, slug, expected, present)
    steps = expected_steps(expected["order"])
    shown_steps = {name: step for name, (step, _) in blocks(page).items()}
    assert shown_steps == steps, (slug, shown_steps)
    assert expected["order"]["workers"] == 1, slug
    assert page.input_value("#workers") == "", (slug, page.input_value("#workers"))
    assert page.get_attribute("#workers", "placeholder") == "1", slug
    missing = sum(1 for p in expected["playbooks"] if p not in present)
    print(f"ok {slug}: {len(paths)} file(s), {len(expected['playbooks'])} shared playbook(s) ({missing} not available), "
          f"{len(expected['notices'])} notice(s), {len(steps)} start step(s) match CPython")


def check_layout(page):
    """Controls left of the shared pane in row 1, Proposed left of Today's in row 2, each control on its own line."""
    box = {name: page.locator(sel).bounding_box() for name, sel in (
        ("controls", ".controls"), ("shared", "section.shared"),
        ("proposed", "section.pane:has(#source)"), ("today", "section.pane:has(#tree)"))}
    assert box["controls"]["x"] + box["controls"]["width"] <= box["shared"]["x"], box
    assert box["proposed"]["x"] + box["proposed"]["width"] <= box["today"]["x"], box
    assert abs(box["controls"]["x"] - box["proposed"]["x"]) < 1, box
    assert abs(box["shared"]["x"] - box["today"]["x"]) < 1, box
    for upper, lower in (("controls", "proposed"), ("shared", "today"), ("controls", "today"), ("shared", "proposed")):
        assert box[upper]["y"] + box[upper]["height"] <= box[lower]["y"], (upper, lower, box)
    controls = [c.bounding_box() for c in page.locator(".controls .control").all()]
    assert len(controls) == 5, controls
    for upper, lower in zip(controls, controls[1:]):
        assert lower["y"] >= upper["y"] + upper["height"], (upper, lower)
    for selector in ("#starter", "#preset", "#scenarios-dir", "#share", "#status"):
        hint = page.locator(f".control:has({selector}) .hint")
        assert hint.count() == 1 and hint.text_content().strip().endswith("."), selector
    for listing, viewer in (("#shared-files", "#shared-file"), ("#source-files", "#source"), ("#tree", "#file")):
        column = page.locator(listing).bounding_box()
        code = page.locator(viewer).bounding_box()
        assert column["x"] + column["width"] <= code["x"], (listing, column, code)
        assert column["y"] <= code["y"], (listing, column, code)
        boxes = [b.bounding_box() for b in page.locator(f"{listing} button.file").all()]
        assert boxes, listing
        for upper, lower in zip(boxes, boxes[1:]):
            assert lower["y"] >= upper["y"] + upper["height"], (listing, upper, lower)
            assert lower["x"] < code["x"], (listing, lower)
    print("ok controls | shared playbooks above proposed | today's, one control per line, file lists left of code")


def check_edit_survives(page):
    """An edit to molecule.yml survives viewing a shared playbook."""
    page.select_option("#preset", "collection")
    page.wait_for_selector("#shared-files button.file[data-kind=playbook]")
    text = page.evaluate("converter.source()") + "# edited\n"
    page.fill(EDITOR, text)
    page.locator("#shared-files button.file[data-kind=playbook]").last.click()
    assert page.is_visible("#source")
    assert page.evaluate("converter.source()") == text, "the edit did not survive viewing a playbook"
    print("ok an edit to molecule.yml survives viewing a shared playbook")


def check_workers(page, schema, shots):
    """Workers defaults to 1, a typed value overrides at once, clearing returns to the file's value or 1."""
    slug = "roles"
    text = example_source(slug).read_text()
    page.select_option("#preset", slug)
    one = expected_steps(convert_text(text, schema, "molecule")["order"])
    wait_for_steps(page, one)
    assert page.input_value("#workers") == "", page.input_value("#workers")
    assert page.get_attribute("#workers", "placeholder") == "1"
    assert page.text_content("#workers-note") == "default", page.text_content("#workers-note")
    assert len(set(one.values())) == len(one), one
    before = blocks(page)
    if shots:
        page.screenshot(path=str(shots / "roles-workers-default.png"), full_page=True)
    three = convert_text(text, schema, "molecule", 3)
    steps = expected_steps(three["order"])
    assert steps != one, (steps, one)
    page.fill("#workers", "3")
    wait_for_steps(page, steps)
    after = blocks(page)
    moved = [n for n in before if before[n][1] != after[n][1]]
    assert moved, (before, after)
    assert page.text_content("#workers-note") == "set here"
    shown_notices = page.locator("#notices li").all_text_contents()
    assert shown_notices == notice_lines(three), shown_notices
    assert any(n["kind"] == "unsupported" for n in three["notices"]), three["notices"]
    if shots:
        page.screenshot(path=str(shots / "roles-workers-3.png"), full_page=True)
    print(f"ok workers 3 redraws at once, moves {len(moved)} block(s) and is unsupported outside a collection")
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
    wait_for_steps(page, steps)
    assert page.input_value("#workers") == "10", page.input_value("#workers")
    assert not page.evaluate("document.getElementById('workers').matches(':invalid')")
    print("ok workers above the scenario count stays as typed and binds nothing")
    page.fill("#workers", "")
    wait_for_steps(page, one)
    assert page.get_attribute("#workers", "placeholder") == "1"
    assert not page.evaluate("document.getElementById('workers').matches(':invalid')")
    print("ok clearing workers returns to 1")
    two_text = text.replace("---\n", "---\nworkers: 2\n", 1)
    page.fill(EDITOR, two_text)
    two = expected_steps(convert_text(two_text, schema, "molecule")["order"])
    wait_for_steps(page, two)
    assert page.get_attribute("#workers", "placeholder") == "2"
    assert page.text_content("#workers-note") == "from molecule.yml"
    page.fill("#workers", "1")
    wait_for_steps(page, one)
    page.fill("#workers", "")
    wait_for_steps(page, two)
    print("ok the file's workers applies when the field is empty, and the field overrides it")
    page.select_option("#preset", "collection")
    page.wait_for_function("document.getElementById('workers').value === ''")
    page.fill("#workers", "2")
    page.select_option("#destroy", "never")
    collection = example_source("collection").read_text()
    never = convert_text(collection, schema, "extensions/molecule", 2, None, "never")
    lines = notice_lines(never)
    page.wait_for_function(
        f"JSON.stringify([...document.querySelectorAll('#notices li')].map(l => l.textContent)) === "
        f"{json.dumps(json.dumps(lines, separators=(',', ':')))}")
    assert any("--destroy=never" in line for line in lines), lines
    print("ok workers above 1 with destroy never is unsupported")
    page.select_option("#preset", "roles")
    page.wait_for_function(
        "document.getElementById('workers').value === '' && document.getElementById('destroy').value === 'always'")
    print("ok loading a preset clears workers and destroy")


def check_typed_missing(page, schema):
    """A playbook named in typed input is listed once in the shared pane and marked not available."""
    page.click("#starter")
    text = ("---\nscenarios:\n  - name: typed\n    playbooks:\n"
            "      verify: playbooks/molecule/verify-typed.yml\n")
    page.fill(EDITOR, text)
    path = "playbooks/molecule/verify-typed.yml"
    assert convert_text(text, schema)["playbooks"] == [path]
    page.wait_for_selector(f'#shared-files button.file[data-path="{path}"]')
    button = page.locator(f'#shared-files button.file[data-path="{path}"]')
    assert button.get_attribute("data-available") == "false"
    assert "missing" in button.get_attribute("class")
    assert "not available" in button.text_content()
    button.click()
    assert page.is_visible("#shared-missing")
    assert page.text_content("#shared-missing") == f"{path} is not part of this input."
    assert page.locator(f'#source-files button.file[data-path="{path}"]').count() == 0
    assert page.locator(f'#tree button.file[data-path="{path}"]').count() == 0
    assert page.evaluate("converter.source()") == text
    print("ok a playbook named in typed input is listed once in the shared pane and marked not available")
    bare = "---\nscenarios:\n  - name: bare\n"
    page.fill(EDITOR, bare)
    page.wait_for_selector("#shared-empty", state="visible")
    assert page.is_hidden("#shared-workspace")
    assert page.locator("#shared-files button.file").count() == 0
    assert "references no playbooks" in page.text_content("#shared-empty")
    print("ok a file that references no playbooks shows a note in the shared pane")


def check_landing(page, schema):
    """A fresh page opens on the collection example, and the Starter button loads the starter file."""
    slug = "collection"
    text = example_source(slug).read_text()
    assert page.evaluate("converter.source()") == text, "page did not open on the collection example"
    assert page.input_value("#preset") == slug, page.input_value("#preset")
    assert page.input_value("#scenarios-dir") == "extensions/molecule", page.input_value("#scenarios-dir")
    expected = convert_text(text, schema, "extensions/molecule")
    page.wait_for_function(f"{SHOWN_PATHS}.join() === {json.dumps(','.join(f['path'] for f in expected['files']))}")
    shared = buttons(page, "#shared-files")
    assert [p for p, _, _ in shared] == expected["playbooks"], shared
    assert all(a for _, _, a in shared), shared
    assert page.input_value("#workers") == "" and page.get_attribute("#workers", "placeholder") == "1"
    print(f"ok the page opens on the {slug} example in extensions/molecule with {len(shared)} shared playbook(s)")
    starter = load_starter()
    page.fill(EDITOR, "")
    page.click("#starter")
    assert page.evaluate("converter.source()") == starter, "the Starter button did not load the starter file"
    assert page.input_value("#preset") == ""
    paths = [f["path"] for f in convert_text(starter, schema)["files"]]
    page.wait_for_function(f"{SHOWN_PATHS}.join() === {json.dumps(','.join(paths))}")
    print(f"ok the Starter button loads the starter file: {len(paths)} file(s)")


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
    assert other.input_value("#preset") == "", other.input_value("#preset")
    print("ok share link round-trips the source and overrides the default landing")
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
        check_landing(page, schema)
        slugs = page.locator("#preset option").evaluate_all("o => o.map(x => x.value).filter(v => v)")
        assert slugs == ["collection", "collection-shared-state", "playbooks", "roles"], slugs
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
