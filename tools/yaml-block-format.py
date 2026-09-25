#!/usr/bin/env python3
"""Reformat YAML files to block style in place.

Flow maps and lists ({a: 1}, [x, y]) become block style; empty {} and [] stay
inline (they have no block form). Comments, quoting, and anchors are preserved.

Run it over example configs after pulling in an upstream repo, so the before/
and after/ trees are in one style and their line counts compare apples to apples.

Requires ruamel.yaml (pip install ruamel.yaml).

    python3 tools/yaml-block-format.py path/to/molecule.yml [more.yml ...]
"""
import sys
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq


def force_block(node):
    # Round-trip loading remembers each node's original flow/block style, so
    # default_flow_style alone will not convert existing flow collections. Walk
    # the tree and force block on every non-empty collection, leaving empty
    # {} and [] as inline flow.
    if isinstance(node, (CommentedMap, CommentedSeq)):
        if len(node) > 0:
            node.fa.set_block_style()
        else:
            node.fa.set_flow_style()
        children = node.values() if isinstance(node, CommentedMap) else node
        for child in children:
            force_block(child)


def format_file(path):
    with open(path) as f:
        raw = f.read()
    # Keep the document-start marker only if the source had one.
    had_start = any(line.strip() == "---" for line in raw.splitlines()[:3])
    yaml = YAML()  # round-trip: keeps comments and anchors
    yaml.default_flow_style = False
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.explicit_start = had_start
    yaml.indent(mapping=2, sequence=4, offset=2)
    data = yaml.load(raw)
    force_block(data)
    with open(path, "w") as f:
        yaml.dump(data, f)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        format_file(p)
