"""Command line front end for the converter.

Usage:
    python3 tools/converter/cli.py <molecule.yml> [--out DIR] [--schema PATH] [--scenarios-dir DIR]
    python3 tools/converter/cli.py <molecule.yml> --order [--workers N] [--scenarios-dir DIR]
    python3 tools/converter/cli.py --starter
"""

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import yaml  # noqa: E402

from project import (  # noqa: E402
    COLLECTION_SCENARIOS_DIR, PROJECT_SCENARIOS_DIR, SCENARIOS_DIRS, referenced_playbooks)
from render import convert_text, dump  # noqa: E402
from starter import starter_text  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA = ROOT / "generated" / "molecule-config.schema.json"
MOLECULE_SCHEMA = ROOT / "vendor" / "molecule.json"


def load_schema(path=DEFAULT_SCHEMA):
    """Load the config schema JSON.

    Args:
        path: path to the generated schema.

    Returns:
        The schema as a dict.
    """
    return json.loads(pathlib.Path(path).read_text())


def load_starter(schema_path=DEFAULT_SCHEMA, molecule_path=MOLECULE_SCHEMA):
    """Render the starter file from the config schema and Molecule's schema.

    Args:
        schema_path: path to the generated config schema.
        molecule_path: path to the vendored Molecule schema.

    Returns:
        The starter YAML text.
    """
    return starter_text(load_schema(schema_path), load_schema(molecule_path))


def example_source(slug):
    """Return the single-file `molecule.yml` of an example.

    Args:
        slug: the directory name under `examples/`.

    Returns:
        `examples/<slug>/molecule.yml`.
    """
    return ROOT / "examples" / slug / "molecule.yml"


def example_root(slug):
    """Return the project root of an example's single-config layout.

    Args:
        slug: the directory name under `examples/`.

    Returns:
        The directory that holds the example's single-file `molecule.yml`.
    """
    return example_source(slug).parent


def example_playbooks(slug):
    """Return the referenced playbooks that exist in an example.

    Args:
        slug: the directory name under `examples/`.

    Returns:
        {project-relative path: file text} for every path `referenced_playbooks` lists
        that names a file inside the example root.
    """
    config = yaml.safe_load(example_source(slug).read_text())
    return playbooks_in(example_root(slug), config, example_scenarios_dir(slug))


def playbooks_in(root, config, scenarios_dir):
    """Return the referenced playbooks that name a file inside a project root.

    A path that is absolute, climbs above the root, or resolves outside it through a
    symlink is left out.

    Args:
        root: the project root directory.
        config: the parsed single-config molecule.yml.
        scenarios_dir: the scenarios directory.

    Returns:
        {project-relative path: file text}.
    """
    root = pathlib.Path(root).resolve()
    found = {}
    for path in referenced_playbooks(config, scenarios_dir):
        if path.startswith("/") or path == ".." or path.startswith("../"):
            continue
        target = (root / path).resolve()
        if target.is_relative_to(root) and target.is_file():
            found[path] = target.read_text()
    return found


def order_text(order):
    """Render a `start_steps` result as one line per step.

    Args:
        order: the `start_steps` result.

    Returns:
        The text, starting with the workers line.
    """
    lines = ["workers: " + ("no limit" if order["workers"] is None else str(order["workers"]))]
    steps = {}
    for item in order["scenarios"]:
        steps.setdefault(item["step"], []).append(item["name"])
    for step in sorted(s for s in steps if s is not None):
        lines.append(f"step {step}: " + ", ".join(steps[step]))
    return "\n".join(lines) + "\n"


def _workers(value):
    try:
        number = int(value)
    except ValueError:
        number = 0
    if number < 1:
        raise argparse.ArgumentTypeError("must be an integer of at least 1")
    return number


def example_scenarios_dir(slug):
    """Return the scenarios directory an example's projection is placed under.

    Args:
        slug: the directory name under `examples/`.

    Returns:
        `extensions/molecule` for a collection (a `galaxy.yml` beside the root file),
        else `molecule`.
    """
    if (example_root(slug) / "galaxy.yml").is_file():
        return COLLECTION_SCENARIOS_DIR
    return PROJECT_SCENARIOS_DIR


def write_tree(result, out):
    """Write projected files and `notices.json` under a directory.

    Args:
        result: the `convert_text` result.
        out: the output directory.
    """
    out = pathlib.Path(out)
    for item in result["files"]:
        target = out / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item["text"])
    (out / "notices.json").write_text(notices_json(result["notices"]))


def notices_json(notices):
    """Render notices as indented JSON text with a trailing newline."""
    return json.dumps(notices, indent=2, ensure_ascii=False) + "\n"


def main(argv=None):
    """Run the CLI. Returns 1 when any notice is an error, else 0."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", nargs="?")
    parser.add_argument("--out")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    parser.add_argument("--starter", action="store_true", help="print the starter file and exit")
    parser.add_argument(
        "--scenarios-dir", choices=SCENARIOS_DIRS, default=COLLECTION_SCENARIOS_DIR,
        help="where scenarios are placed: extensions/molecule for a collection (default), "
             "molecule for a standalone role or playbook project")
    parser.add_argument("--order", action="store_true", help="print the step each scenario starts at and exit")
    parser.add_argument(
        "--workers", type=_workers,
        help="with --order, the most scenarios that start per step (default: no limit)")
    args = parser.parse_args(argv)
    if args.workers is not None and not args.order:
        parser.error("--workers needs --order")
    if args.starter:
        print(load_starter(args.schema), end="")
        return 0
    if not args.source:
        parser.error("a source file is required unless --starter is given")
    result = convert_text(pathlib.Path(args.source).read_text(), load_schema(args.schema), args.scenarios_dir,
                          args.workers)
    if args.order:
        print(order_text(result["order"]), end="")
    elif args.out:
        write_tree(result, args.out)
    else:
        for item in result["files"]:
            print(f"# {item['path']}")
            print(item["text"])
        print("# notices")
        print(dump(result["notices"]))
    return 1 if any(n["kind"] == "error" for n in result["notices"]) else 0


if __name__ == "__main__":
    sys.exit(main())
