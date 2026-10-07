"""Command line front end for the converter.

Usage:
    python3 tools/converter/cli.py <molecule.yml> [--out DIR] [--schema PATH]
    python3 tools/converter/cli.py --starter
"""

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

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
        `examples/<slug>/molecule.yml` for a synthetic example, else `examples/<slug>/after/molecule.yml`.
    """
    root_file = ROOT / "examples" / slug / "molecule.yml"
    return root_file if root_file.is_file() else ROOT / "examples" / slug / "after" / "molecule.yml"


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
    args = parser.parse_args(argv)
    if args.starter:
        print(load_starter(args.schema), end="")
        return 0
    if not args.source:
        parser.error("a source file is required unless --starter is given")
    result = convert_text(pathlib.Path(args.source).read_text(), load_schema(args.schema))
    if args.out:
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
