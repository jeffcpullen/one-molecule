"""Emit the one generated file in this repo, and gate the design corpus.

The design corpus is the YAML under `design/data/`, validated by the schemas in
`design/structure/`. Nothing is rendered from it. The only generated artifact is
the deliverable JSON Schema:

  spec/molecule-config.schema.yml  ->  generated/molecule-config.schema.json

Keys whose name starts with `_` are source-only and are stripped on the way out,
so the YAML can carry notes the JSON artifact never sees.

Run:  python3 tools/build.py            # write the generated schema
      python3 tools/build.py --check    # exit 1 if it is stale, or a lint fails

Both modes also run two linters over the published tree: house writing style
(lint_prose on the design data, lint_prose_text on published markdown) and
lint_clean_room (no private working context in published text). The published
tree is design/ and spec/, the repo-root markdown in PUBLISHED_ROOT_MD, and the
few agent-config files that are published on purpose, in PUBLISHED_EXTRA. The
clean-room rules for personal and private tool names also run on every other
tracked file.

Lint the examples against the generated schema (no code here):
      check-jsonschema --schemafile generated/molecule-config.schema.json \\
          examples/*/molecule.yml examples/*/after/molecule.yml
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_SRC = ROOT / "spec" / "molecule-config.schema.yml"
SCHEMA_JSON = ROOT / "generated" / "molecule-config.schema.json"
DATA = ROOT / "design" / "data"
DESIGN = ROOT / "design"
SPEC = ROOT / "spec"

JSON_MARKER = "x-generated"


# ---------------------------------------------------------------- house style

# House writing style: no semicolons and no dashes in prose. Enforced on the
# string values of the design data, which is the corpus a reader reads. Code is
# exempt, so inline `code` spans are stripped before the scan and a code block's
# body is skipped entirely (a semicolon in a shell snippet is syntax, not prose).
FORBIDDEN = {";": "semicolon", "—": "em dash", "–": "en dash"}

# Keys whose value is code, not prose, and so exempt from the style scan.
CODE_KEYS = ("body", "grammar", "precedence", "chain")


def lint_prose(node, path="", key=None):
    """Return [(path, name, value)] for forbidden punctuation in prose strings."""
    problems = []
    if isinstance(node, dict):
        for k, v in node.items():
            problems += lint_prose(v, f"{path}.{k}" if path else str(k), k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            problems += lint_prose(v, f"{path}[{i}]", key)
    elif isinstance(node, str):
        if key in CODE_KEYS:
            return problems
        prose = re.sub(r"`[^`]*`", "", node)  # drop inline code spans
        for ch, name in FORBIDDEN.items():
            if ch in prose:
                problems.append((path, name, node.strip()))
    return problems


PROSE_MUST_CATCH = [
    {"rules": ["the run is the unit; the scenario is not"]},
    {"intro": "a node inherits from its parent — always"},
]

PROSE_MUST_ALLOW = [
    {"rules": ["the flag is `--all-scenarios; deprecated`"]},
    {"code": [{"body": "run(); done()"}]},
]


def lint_prose_text(text):
    """Return [(lineno, name, line)] for forbidden punctuation in markdown prose.

    The same house style as lint_prose, applied to a text file rather than a
    parsed source. A fenced block is skipped whole and an inline code span is
    stripped, so punctuation that is syntax is not read as prose.
    """
    problems = []
    in_fence = False
    for i, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        prose = re.sub(r"`[^`]*`", "", line)
        for ch, name in FORBIDDEN.items():
            if ch in prose:
                problems.append((i, name, line.strip()))
    return problems


PROSE_TEXT_MUST_CATCH = [
    "the run is the unit; the scenario is not",
    "a node inherits from its parent — always",
    "the range is 1–3 levels deep",
]

PROSE_TEXT_MUST_ALLOW = [
    "the flag is `--all-scenarios; deprecated`",
    "```console\nrun(); done()\n```",
]


def selftest_prose():
    """Return a list of failures for the house-style fixtures."""
    failures = []
    for doc in PROSE_MUST_CATCH:
        if not lint_prose(doc):
            failures.append(f"prose: should have been caught but was not: {doc!r}")
    for doc in PROSE_MUST_ALLOW:
        if lint_prose(doc):
            failures.append(f"prose: should have been allowed but was flagged: {doc!r}")
    for line in PROSE_TEXT_MUST_CATCH:
        if not lint_prose_text(line):
            failures.append(f"prose text: should have been caught but was not: {line!r}")
    for line in PROSE_TEXT_MUST_ALLOW:
        if lint_prose_text(line):
            failures.append(f"prose text: should have been allowed but was flagged: {line!r}")
    return failures


# ------------------------------------------------------------------ clean room

# Clean room: design/ and spec/ are published, so nothing under them may carry
# the private working context they were authored in. This scans every file and
# exempts nothing, since a home path inside a fenced example is precisely the leak.
#
# All internal working material lives under the repo-root `internal/`, which is
# gitignored. These names are the citation denylist: a published doc that points
# at one of them gives a public reader a dead link.
UNPUBLISHED = ("internal", "diagrams", "outward", "showcases", "process", "research")

# Docs legitimately draw example trees under `~/work/`, which names nothing real.
# Every other home-relative path is this machine's layout, so the allow-list is
# deliberately one entry: a new illustrative root has to be added on purpose.
ILLUSTRATIVE_HOME = "work"

# A licence or copyright statement names its holder on purpose, and that is the
# one place a personal name is published rather than leaked. It exempts only the
# attribution rule, and only on the line that carries the notice.
COPYRIGHT_LINE = re.compile(r"copyright|\(c\)|SPDX-FileCopyrightText", re.IGNORECASE)

# Each entry is (pattern, name, exempt, everywhere). `exempt` is a pattern that,
# when it matches the same line, means the line is deliberate rather than a leak.
# `everywhere` rules run on every tracked file. The others run on the published
# text only, since generic home paths and folder names are ordinary in code.
CLEAN_ROOM = [
    (re.compile(r"/home/|~/(?!%s/)" % ILLUSTRATIVE_HOME), "personal filesystem path", None, False),
    # A trailing name is what makes it a dead link. Naming the folder itself is
    # allowed, since the conventions have to be able to say where things go.
    (re.compile(r"""(?:^|[\s`(/"'])(?:%s)/[\w-]""" % "|".join(UNPUBLISHED)),
     "pointer to a file in an unpublished directory", None, False),
    (re.compile(r"\.claude"), "private tooling reference", None, False),
    # Case-insensitive, so a home path or an address carrying the name is caught.
    (re.compile(r"\bJeff\b", re.IGNORECASE), "personal attribution", COPYRIGHT_LINE, True),
]

# Names of private tools and repos are kept in an ignored file beside this one,
# so the gate can catch them without publishing them. One regex per line, `#`
# starts a comment. A clone without the file runs every other clean-room rule.
PRIVATE_NAMES_FILE = Path(__file__).resolve().parent / "private-names.txt"


def load_private_names(path=PRIVATE_NAMES_FILE):
    """Return the regex entries in the private names file, or [] if it is absent."""
    if not path.is_file():
        return []
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def private_names_pattern(entries):
    """Return one regex matching any entry, or None when there are none."""
    return re.compile("|".join(entries)) if entries else None


_PRIVATE_NAMES = private_names_pattern(load_private_names())
if _PRIVATE_NAMES:
    CLEAN_ROOM.append((_PRIVATE_NAMES, "private tooling reference", None, True))


def lint_clean_room(text, everywhere_only=False):
    """Return [(lineno, name, line)] for private working context in text.

    With everywhere_only, only the rules that apply to every tracked file run."""
    problems = []
    for i, line in enumerate(text.splitlines(), 1):
        for pattern, name, exempt, everywhere in CLEAN_ROOM:
            if everywhere_only and not everywhere:
                continue
            if pattern.search(line) and not (exempt and exempt.search(line)):
                problems.append((i, name, line.strip()))
    return problems


# A gate with no fixture that proves it fires is not trustworthy: a pattern that
# silently stops matching passes everything. These run as part of --check, so CI
# fails if the clean-room rules are ever loosened by accident.
CLEAN_ROOM_MUST_CATCH = [
    "see `internal/HANDOFF.md` for more",
    "Rejected in `diagrams/BRIEF.md`",
    "Start at `showcases/HANDOFF.md`",
    "see outward/pr-body.md",
    # A citation opening with a quote is the form the corpus used most, so the
    # prefix class has to admit it or the gate passes the exact case it exists for.
    'evidence: "research/lint-notes.md"',
    "the reasoning lives in ../research/state-notes.md",
    "run ~/repos/some-tool/run.sh",
    "the agent brief under .claude/agents/",
    "a path under /home/someone/repos",
    "a note Jeff left in the margin",
    "ask Jeff before changing this",
]

# The private names list is proved with a synthetic entry, since the real names
# are the thing being kept out of this file.
PRIVATE_NAMES_FIXTURE = ["example-private-runner"]
PRIVATE_NAMES_MUST_CATCH = ["run example-private-runner before pushing"]
PRIVATE_NAMES_MUST_ALLOW = ["run the repo gates before pushing"]

CLEAN_ROOM_MUST_ALLOW = [
    "| `internal/` | All working material. Gitignored |",
    "anything that is not publishable goes under `internal/`.",
    "history and implementation notes go to the internal working notes.",
    "the tree under ~/work/acme-automation/ is the project root",
    "Licensed under Apache-2.0, copyright 2026 Jeff Pullen.",
]

# The rules that run on every tracked file, which is mostly code and config.
TRACKED_MUST_CATCH = [
    "    owner: jeff",
    "# ask Jeff before changing this",
]

TRACKED_MUST_ALLOW = [
    "    ANSIBLE_COLLECTIONS_PATH: /home/zuul/.ansible/collections",
    "    ANSIBLE_ROLES_PATH: ~/.cache/molecule/roles",
    "internal/",
    "!.claude/agents/om-design-author.md",
    "Copyright 2026 Jeff Pullen",
]


def selftest_clean_room():
    """Return a list of failures for the clean-room fixtures."""
    failures = []
    for line in CLEAN_ROOM_MUST_CATCH:
        if not lint_clean_room(line):
            failures.append(f"clean room: should have been caught but was not: {line!r}")
    for line in CLEAN_ROOM_MUST_ALLOW:
        if lint_clean_room(line):
            failures.append(f"clean room: should have been allowed but was flagged: {line!r}")
    for line in TRACKED_MUST_CATCH:
        if not lint_clean_room(line, everywhere_only=True):
            failures.append(f"tracked files: should have been caught but was not: {line!r}")
    for line in TRACKED_MUST_ALLOW:
        if lint_clean_room(line, everywhere_only=True):
            failures.append(f"tracked files: should have been allowed but was flagged: {line!r}")
    pattern = private_names_pattern(PRIVATE_NAMES_FIXTURE)
    for line in PRIVATE_NAMES_MUST_CATCH:
        if not pattern.search(line):
            failures.append(f"private names: should have been caught but was not: {line!r}")
    for line in PRIVATE_NAMES_MUST_ALLOW:
        if pattern.search(line):
            failures.append(f"private names: should have been allowed but was flagged: {line!r}")
    if private_names_pattern([]) is not None:
        failures.append("private names: an empty list must add no rule")
    return failures


# Four files under the local agent-config folder are published on purpose: the
# three agent definitions and the update-the-docs skill. They sit outside design/
# and spec/, so they are named here or the gates never see them. The same
# carve-outs are spelled out in .gitignore and tools/private-paths.txt.
PUBLISHED_EXTRA = (
    ROOT / ".claude" / "agents" / "om-content-converter.md",
    ROOT / ".claude" / "agents" / "om-design-author.md",
    ROOT / ".claude" / "agents" / "om-docs-maintainer.md",
    ROOT / ".claude" / "skills" / "update-the-docs" / "SKILL.md",
)

# The repo-root markdown a public reader lands on first. They sit outside
# design/ and spec/, so they are named here or the gates never see them.
PUBLISHED_ROOT_MD = (
    ROOT / "README.md",
    ROOT / "NOTICES.md",
    ROOT / "AGENTS.md",
    ROOT / "CONTRIBUTING.md",
)


def published_files():
    """Every published text file: everything under design/ and spec/, the
    repo-root markdown, plus the handful of agent-config files that are
    published on purpose."""
    for root in (DESIGN, SPEC):
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix in (".md", ".yml", ".yaml", ".json"):
                yield path
    for path in PUBLISHED_ROOT_MD + PUBLISHED_EXTRA:
        if path.is_file():
            yield path


# This file spells out the patterns in its fixtures, so it cannot scan itself.
GATE_DEFINITION = Path(__file__).resolve()


def tracked_files():
    """Every text file git tracks, outside the published set and this file."""
    published = set(published_files())
    listing = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"],
                             capture_output=True, check=True, text=True).stdout
    for rel in listing.split("\0"):
        path = ROOT / rel
        if not rel or path in published or path == GATE_DEFINITION or not path.is_file():
            continue
        try:
            yield path, path.read_text()
        except UnicodeDecodeError:
            continue


# -------------------------------------------------------------------- generate


def strip_source_only(node):
    """Drop every `_`-prefixed key, recursively. Source-only, never emitted."""
    if isinstance(node, dict):
        return {k: strip_source_only(v) for k, v in node.items() if not k.startswith("_")}
    if isinstance(node, list):
        return [strip_source_only(v) for v in node]
    return node


def load_schema():
    """The config schema source, with source-only keys stripped and drift checked."""
    schema = strip_source_only(yaml.safe_load(SCHEMA_SRC.read_text()))
    # The config-key list appears twice by necessity (closed `config` overlay for
    # `defaults:`, and the same keys inline on `node` for bare use). Guard the two
    # against drift so the single source stays self-consistent.
    cfg = set(schema["definitions"]["config"]["properties"])
    node_cfg = {k for k, p in schema["definitions"]["node"]["properties"].items()
                if p.get("x-class") == "config"}
    if cfg != node_cfg:
        raise SystemExit(f"schema config keys drifted: config={sorted(cfg)} node={sorted(node_cfg)}")
    return schema


# Every spec version is a git tag `v<version>`. The `$id` names that tag and the
# description names the version, so a bump that misses either is caught here.
SPEC_ID = "https://raw.githubusercontent.com/jeffcpullen/one-molecule/v{v}/generated/molecule-config.schema.json"


def lint_spec_version(schema):
    """Return problems where `$id` or the description disagree with `x-spec.version`."""
    version = str(schema.get("x-spec", {}).get("version", ""))
    if not version:
        return ["x-spec.version is missing"]
    problems = []
    if schema.get("$id") != SPEC_ID.format(v=version):
        problems.append(f"$id does not name tag v{version}")
    if f"version {version}" not in schema.get("description", ""):
        problems.append(f"description does not name version {version}")
    return problems


SPEC_VERSION_MUST_CATCH = [
    {"$id": SPEC_ID.format(v="0.1.0"), "description": "version 0.2.0", "x-spec": {"version": "0.2.0"}},
    {"$id": SPEC_ID.format(v="0.2.0"), "description": "version 0.1.0", "x-spec": {"version": "0.2.0"}},
    {"$id": SPEC_ID.format(v="0.2.0"), "description": "version 0.2.0"},
]
SPEC_VERSION_MUST_ALLOW = [
    {"$id": SPEC_ID.format(v="0.2.0"), "description": "x, version 0.2.0: y", "x-spec": {"version": "0.2.0"}},
]


def selftest_spec_version():
    """Return a list of failures for the spec-version fixtures."""
    failures = []
    for doc in SPEC_VERSION_MUST_CATCH:
        if not lint_spec_version(doc):
            failures.append(f"spec version: should have been caught but was not: {doc!r}")
    for doc in SPEC_VERSION_MUST_ALLOW:
        if lint_spec_version(doc):
            failures.append(f"spec version: should have been allowed but was flagged: {doc!r}")
    return failures


def render_json():
    """The JSON artifact text for the config schema source."""
    schema = load_schema()
    schema.pop(JSON_MARKER, None)
    marked = {JSON_MARKER: f"GENERATED from spec/{SCHEMA_SRC.name} by tools/build.py. "
                           "Do not edit by hand."}
    marked.update(schema)
    return json.dumps(marked, indent=2, ensure_ascii=False) + "\n"


# ------------------------------------------------------------------------ main


def main(argv):
    check = "--check" in argv
    rc = 0

    failures = selftest_clean_room() + selftest_prose() + selftest_spec_version()
    if failures:
        rc = 1
        print("SELFTEST: the lint patterns no longer behave as specified:", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
    else:
        print("OK: lint selftests passed.")

    for problem in lint_spec_version(load_schema()):
        rc = 1
        print(f"SPEC VERSION: {SCHEMA_SRC.name}: {problem}", file=sys.stderr)

    text = render_json()
    if check:
        current = SCHEMA_JSON.read_text() if SCHEMA_JSON.exists() else ""
        if current != text:
            print(f"STALE: {SCHEMA_JSON} does not match {SCHEMA_SRC.name}. "
                  f"Run: python3 tools/build.py", file=sys.stderr)
            rc = 1
        else:
            print(f"OK: {SCHEMA_JSON} is up to date.")
    else:
        SCHEMA_JSON.parent.mkdir(parents=True, exist_ok=True)
        SCHEMA_JSON.write_text(text)
        print(f"Wrote {SCHEMA_JSON}")

    for src in sorted(DATA.glob("*.yml")):
        problems = lint_prose(yaml.safe_load(src.read_text()))
        if problems:
            rc = 1
            print(f"PROSE: {src.name} has forbidden punctuation (house style: no "
                  f"semicolons or dashes in prose):", file=sys.stderr)
            for where, name, ctx in problems:
                print(f"  {src.name}: {where}: {name}: {ctx}", file=sys.stderr)

    for path in published_files():
        body = path.read_text()
        rel = path.relative_to(ROOT)
        problems = lint_clean_room(body)
        if problems:
            rc = 1
            print(f"CLEAN ROOM: {rel} carries private working context "
                  f"(it is published, so move it to internal/ or reword):", file=sys.stderr)
            for ln, name, ctx in problems:
                print(f"  {rel}:{ln}: {name}: {ctx}", file=sys.stderr)
        if path.suffix != ".md":
            continue
        problems = lint_prose_text(body)
        if problems:
            rc = 1
            print(f"PROSE: {rel} has forbidden punctuation (house style: no "
                  f"semicolons or dashes in prose):", file=sys.stderr)
            for ln, name, ctx in problems:
                print(f"  {rel}:{ln}: {name}: {ctx}", file=sys.stderr)

    for path, body in tracked_files():
        rel = path.relative_to(ROOT)
        problems = lint_clean_room(body, everywhere_only=True)
        if problems:
            rc = 1
            print(f"CLEAN ROOM: {rel} carries a private name "
                  f"(it is tracked, so it is public on push):", file=sys.stderr)
            for ln, name, ctx in problems:
                print(f"  {rel}:{ln}: {name}: {ctx}", file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
