"""Stage the converter page into a directory for the Pages build.

Usage:
    python3 tools/converter/stage_pages.py <dest>
"""

import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCHEMA = ROOT / "generated" / "molecule-config.schema.json"
MODULES = ["project.py", "render.py"]


def stage(dest):
    """Copy the page, the Python modules, the schema and the fixture-covered examples.

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
    examples = dest / "examples"
    examples.mkdir(exist_ok=True)
    slugs = sorted(p.name for p in (HERE / "fixtures").iterdir() if p.is_dir())
    for slug in slugs:
        shutil.copy2(ROOT / "examples" / slug / "after" / "molecule.yml", examples / f"{slug}.yml")
    (dest / "presets.json").write_text(json.dumps(slugs) + "\n")


if __name__ == "__main__":
    stage(sys.argv[1])
