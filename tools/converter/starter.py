"""Build a starter single-config molecule.yml that lists every key the spec declares.

Standard library only. Keys and notes come from the config schema, and the sub-keys of
Molecule's own sections from Molecule's schema, resolved through the spec's `$ref`s.
"""

from project import KeyClasses

MOLECULE_REF = "../vendor/molecule.json#"
LIVE_NAME = "integration_sample_filter"
MAX_ENUM_VALUES = 5
LIVE_DEFAULTS = {
    "playbooks": {
        "cleanup": "../utils/playbooks/noop.yml",
        "converge": "../utils/playbooks/converge.yml",
        "destroy": "../utils/playbooks/noop.yml",
        "prepare": "../utils/playbooks/noop.yml",
    },
    "platforms": [{"name": "na"}],
    "provisioner": {
        "name": "ansible",
        "config_options": {"defaults": {"collections_path": "${ANSIBLE_COLLECTIONS_PATH}"}},
    },
    "scenario": {
        "test_sequence": ["prepare", "converge"],
        "destroy_sequence": ["destroy"],
    },
}
HEADER = [
    "---",
    "# Starter molecule.yml for spec {version}, generated from the config schema.",
    "# The live lines follow the ansible-creator collection scaffold: shared config in the",
    "# defaults block, one integration_<target> scenario per integration test target.",
    "# Uncomment a key to use it. Molecule's own sections list their keys one level deep.",
    "# Every config key shown under the scenario also works under defaults:, for every scenario.",
]


def _pointer(doc, path):
    node = doc
    for part in path.strip("/").split("/"):
        if part:
            node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def _first_sentence(text):
    text = " ".join(text.split())
    end = text.find(". ")
    return text if end < 0 else text[:end + 1]


class _Schemas:
    """Resolve subschemas across the config schema and Molecule's schema."""

    def __init__(self, schema, molecule):
        self.schema = schema
        self.molecule = molecule

    def resolve(self, sub, doc):
        """Follow `$ref`s. Returns the resolved subschema and the document it lives in."""
        while isinstance(sub, dict) and "$ref" in sub:
            ref = sub["$ref"]
            if ref.startswith(MOLECULE_REF):
                doc, path = self.molecule, ref[len(MOLECULE_REF):]
            elif ref.startswith("#"):
                path = ref[1:]
            else:
                return {}, doc
            sub = _pointer(doc, path)
        return sub, doc

    def variants(self, sub, doc):
        """Flatten `anyOf`, `oneOf` and `allOf` into resolved (subschema, doc) pairs."""
        sub, doc = self.resolve(sub, doc)
        out = [(sub, doc)]
        for key in ("anyOf", "oneOf", "allOf"):
            for item in sub.get(key, []):
                out.extend(self.variants(item, doc))
        return out

    def properties(self, sub, doc):
        """Return {key: (subschema, doc)} across every variant, first declaration wins."""
        props = {}
        for variant, vdoc in self.variants(sub, doc):
            for key, value in variant.get("properties", {}).items():
                props.setdefault(key, (value, vdoc))
        return props

    def kind(self, sub, doc):
        """Short type hint, such as `string`, `list` or `one of: a, b`.

        An enum longer than `MAX_ENUM_VALUES` is not listed.
        """
        kinds = []
        long_enums = []
        for variant, _ in self.variants(sub, doc):
            if "enum" in variant:
                values = [str(v) for v in variant["enum"] if v is not None]
                if len(values) <= MAX_ENUM_VALUES:
                    kinds.append("one of: " + ", ".join(values))
                else:
                    long_enums.append(len(values))
                continue
            types = variant.get("type", [])
            for name in types if isinstance(types, list) else [types]:
                label = {"array": "list", "object": "mapping"}.get(name, name)
                if name != "null" and label not in kinds:
                    kinds.append(label)
        if not kinds and long_enums:
            kinds.append(f"one of {max(long_enums)} values")
        return " or ".join(kinds)

    def note(self, sub, doc):
        """The key's own description, else the resolved one, else its type hint."""
        if isinstance(sub, dict) and sub.get("description"):
            return _first_sentence(sub["description"])
        resolved, rdoc = self.resolve(sub, doc)
        if resolved.get("description"):
            return _first_sentence(resolved["description"])
        return self.kind(sub, doc)


def _line(indent, text, note, commented=True):
    body = f"{text}  # {note}" if note else text
    return " " * indent + ("# " if commented else "") + body


def _value_lines(value, indent):
    """Render a live value in block style, one key or item per line."""
    pad = " " * indent
    lines = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.extend(_value_lines(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {item}")
    else:
        for item in value:
            if isinstance(item, dict):
                inner = _value_lines(item, indent + 2)
                lines.append(f"{pad}- {inner[0].lstrip()}")
                lines.extend(inner[1:])
            else:
                lines.append(f"{pad}- {item}")
    return lines


def starter_text(schema, molecule):
    """Render the starter file.

    Args:
        schema: the config schema as a dict (generated JSON form).
        molecule: Molecule's own schema as a dict (vendored molecule.json).

    Returns:
        YAML text with a live `defaults:` block holding the `LIVE_DEFAULTS` values, one live
        scenario named `LIVE_NAME`, and every other declared key commented out.
    """
    schemas = _Schemas(schema, molecule)
    classes = KeyClasses(schema)
    run = schema["properties"]
    node = schema["definitions"]["node"]["properties"]
    version = schema.get("x-spec", {}).get("version", "")
    lines = [h.format(version=version) for h in HEADER]

    catalog = schemas.properties(run["platforms"]["items"], schema)
    lines.append("")
    lines.append(_line(0, "platforms:", schemas.note(run["platforms"], schema)))
    for i, (key, (sub, doc)) in enumerate(catalog.items()):
        lines.append(_line(2, ("- " if i == 0 else "  ") + f"{key}:", schemas.note(sub, doc)))

    lines.append("")
    lines.append(_line(0, "defaults:", schemas.note(run["defaults"], schema), commented=False))
    for key in classes.config_order:
        live = LIVE_DEFAULTS.get(key)
        lines.append(_line(2, f"{key}:", schemas.note(node[key], schema), commented=live is None))
        if live is not None:
            lines.extend(_value_lines(live, 4))

    lines.append("")
    lines.append(_line(0, "scenarios:", schemas.note(run["scenarios"], schema), commented=False))
    lines.append(_line(2, f"- name: {LIVE_NAME}", schemas.note(node["name"], schema), commented=False))
    for key, sub in node.items():
        if key in ("name", "children"):
            continue
        default = sub.get("default")
        text = f"{key}: {default}" if default is not None else f"{key}:"
        lines.append(_line(4, text, schemas.note(sub, schema)))
        if classes.is_config(key) and schemas.kind(sub, schema) != "list":
            for subkey, (child, cdoc) in schemas.properties(sub, schema).items():
                lines.append(_line(6, f"{subkey}:", schemas.note(child, cdoc)))
    if "children" in node:
        lines.append(_line(4, "children:", schemas.note(node["children"], schema)))
        lines.append(_line(6, "- name:", "A child takes every key a scenario takes."))
    return "\n".join(lines) + "\n"
