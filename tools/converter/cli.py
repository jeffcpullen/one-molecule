"""Command line front end for the converter.

Usage:
    python3 tools/converter/cli.py <molecule.yml> [--out DIR] [--schema PATH]
"""

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from render import convert_text, dump  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA = ROOT / "generated" / "molecule-config.schema.json"


def load_schema(path=DEFAULT_SCHEMA):
    """Load the config schema JSON.

    Args:
        path: path to the generated schema.

    Returns:
        The schema as a dict.
    """
    return json.loads(pathlib.Path(path).read_text())


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
    parser.add_argument("source")
    parser.add_argument("--out")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    args = parser.parse_args(argv)
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
