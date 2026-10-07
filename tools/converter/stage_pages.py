"""Stage the converter page into a directory for the Pages build.

Usage:
    python3 tools/converter/stage_pages.py <dest>
"""

import hashlib
import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from cli import example_playbooks, example_scenarios_dir, example_source, load_starter  # noqa: E402

SCHEMA = ROOT / "generated" / "molecule-config.schema.json"
MODULES = ["project.py", "render.py"]


def stage(dest):
    """Copy the page, the Python modules and the schema, and write the presets and the starter file.

    The presets are the fixture-covered examples, each with the scenarios directory its
    fixture is projected under, and the text of every referenced playbook that exists in
    the example. The starter lists every key the spec declares.

    No staged file starts with `---`, so the Jekyll build copies every one unchanged.

    Args:
        dest: the output directory.
    """
    dest = pathlib.Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for item in (HERE / "web").iterdir():
        shutil.copy2(item, dest / item.name)
    for name in MODULES:
        shutil.copy2(HERE / name, dest / name)
    shutil.copy2(SCHEMA, dest / SCHEMA.name)
    slugs = sorted(p.name for p in (HERE / "fixtures").iterdir() if p.is_dir())
    presets = {slug: {"text": example_source(slug).read_text(), "scenarios_dir": example_scenarios_dir(slug),
                      "playbooks": example_playbooks(slug)}
               for slug in slugs}
    (dest / "presets.json").write_text(json.dumps(presets, indent=2) + "\n")
    (dest / "starter.json").write_text(json.dumps({"text": load_starter()}, indent=2) + "\n")
    digest = hashlib.sha256()
    for name in [*MODULES, SCHEMA.name, "presets.json", "starter.json"]:
        digest.update((dest / name).read_bytes())
    (dest / "build.json").write_text(json.dumps({"version": digest.hexdigest()[:16]}) + "\n")
    for path in dest.rglob("*"):
        if path.is_file() and path.read_bytes().startswith(b"---"):
            raise SystemExit(f"{path} starts with ---, which Jekyll would render as a page")


if __name__ == "__main__":
    stage(sys.argv[1])
