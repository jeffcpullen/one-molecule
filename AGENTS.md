# Ground rules for AI agents

Read this before changing anything. It applies to any AI coding tool and to the human driving it.
These rules exist because this repo is published and easy to quietly corrupt.

## 1. The folder name says whether you may edit what is inside.

| Folder | Holds | Hand-edit |
|---|---|---|
| `design/data/` | The design corpus, one YAML source per subject | Yes |
| `design/structure/` | One validator per source, plus the shared shapes | Yes |
| `design/docs/` | The Diataxis documentation set | Yes, by its own process |
| `spec/` | The authored source of the deliverable config schema | Yes |
| `generated/` | `molecule-config.schema.json`, emitted by `tools/build.py` | No |
| `vendor/` | `molecule.json`, vendored from upstream molecule | No, re-vendor |

There is no rendered design page any more. The YAML under `design/data/` is the corpus, and it is what
a reader reads. Editing `generated/` is overwritten by the next build and fails CI. There is no
exception for "just a typo".

To change the config surface, edit `spec/molecule-config.schema.yml` and run `python3 tools/build.py`.

## 2. `design/` and `spec/` are a clean room.

They are published. Nothing under them may carry the private context they were authored in:

- no home-relative path (the one exception is the illustrative `~/work/` used in example trees)
- no name of local-only tooling
- no pointer to a gitignored folder, because a public reader only gets a dead link
- no personal attribution by name

`tools/build.py` enforces this with `lint_clean_room`. If it fails, do not reword to dodge the pattern.
Move the content to an internal folder, or cite something a public reader can actually open.

## 3. Internal folders are internal.

All internal working material lives under one root, `internal/`, which is gitignored: research notes,
process scaffolding, rendered assets and outward drafts. The local agent config is ignored too, apart
from the three agent definitions and the one skill that are published on purpose and are gated like
anything else under `design/`.
Never `git add -f` any of it, never cite it from a published doc, and never copy its content into one.

The rule is simple. If it is tracked, it is publishable. If it is not publishable, it goes under
`internal/`.

`tools/check-private-paths.sh` blocks a push that would publish any of them. Install the hook once per
clone:

```console
./tools/install-hooks.sh
```

## 4. Stage explicit paths.

Never `git add -A` and never `git commit -a`. Another session may share this working tree, and a blanket
add is how internal material becomes a public commit. Name the files you changed.

## 5. Writing style is enforced.

No semicolons. No em dashes or en dashes. No smart quotes. The validators reject them in source strings
and `tools/build.py lint_prose` rejects them across the design data. Author clean YAML rather than
fighting the linter.

One idea per entry. A rule, a table cell, or a definition states one thing. Design sources carry
normative current-state content only: what the tool does, never the reasoning or the alternative that
lost.

## 6. Verify. Do not assert.

A change is done when the gates are green, not when it looks right. Run them and read the output:

```console
python3 tools/build.py --check
yamllint --strict -c .yamllint .
./tools/check-private-paths.sh
```

Validate an edited source against its validator:

```console
check-jsonschema --schemafile design/structure/<doc>.schema.yml design/data/<doc>.yml
```

All of the above also run through `pre-commit` from the repo root.

A grep hit is not evidence. A silent replace is not evidence. Read back what you changed, and never
report a result you did not run.

## 7. Scope.

Make the change that was asked for. A question is not approval to widen scope. If a fix belongs in a
file outside what you were asked to touch, say so rather than reaching for it. When you are corrected,
fix the whole class of problem, not just the one instance.

## Where to start

`design/README.md` is the index to the corpus. `design/AUTHORING.md` is the standard for authoring a
source. `tree-spec` is the reference implementation to copy: `design/data/tree-spec.yml` validated by
`design/structure/tree-spec.schema.yml`.
