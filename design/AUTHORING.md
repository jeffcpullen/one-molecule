# Authoring a design source

The design corpus is the YAML under `data/`. There is no rendered page and no generate step. What you
write in `data/<doc>.yml` is what a reader reads, so it carries the writing law as well as the shape.

Every source is validated by `structure/<doc>.schema.yml`, named on the source's first line as a
`yaml-language-server` modeline. `tree-spec` is the reference implementation to copy.

## The rules

1. **One idea per entry.** A rule, a table cell, or a definition states one thing. Do not stack
   independent assertions into one entry unless the coupling is genuine, such as a single conditional
   or a claim with the exception that only means anything attached to it. This is a review norm, and a
   schema cannot judge it.
2. **Normative, current-state content only.** State the rule, never the reasoning behind it. What the
   tool does, not how the code does it and not why an alternative lost. A source reads as the design
   now, never as a decision log.
3. **No semicolons, no em dashes, no en dashes.** Split the clauses into two entries, or reword. The
   schemas reject them in source strings and `tools/build.py` rejects them across the data.
4. **Prose that does not fit moves out.** Rejected alternatives and decisions go to
   `data/rejected-ideas.yml`. Open items go to `data/open-questions.yml`. Research, feasibility,
   defect analysis, history and implementation notes go to the internal working notes, which are
   unpublished, so the corpus moves the content there and does not cite it. A source states a fact
   or omits it, and never points a reader at a note they cannot open. Move that content, never
   drop it.
5. **A new doc gets a bounded schema.** Write `structure/<doc>.schema.yml` shaped to what the doc
   actually holds, with `additionalProperties: false` at every level, required keys, and bounded text
   fields. Never widen the shared `sectioned` shape to admit free prose. Reuse `sectioned` only when
   the doc genuinely is sectioned atomic rules and tables.
6. **Every rule needs a fixture that proves it fires.** A check that silently stops matching passes
   everything. The clean-room and house-style linters in `tools/build.py` carry must-catch and
   must-allow fixtures, and a new gate carries its own.
7. **`generated/` and `vendor/` are never hand-edited.** `generated/molecule-config.schema.json` is
   emitted from `../spec/molecule-config.schema.yml` by `tools/build.py`, and a hand edit is silently
   overwritten by the next build. `vendor/molecule.json` comes from upstream molecule and is
   re-vendored, never patched in place.
8. **`design/` and `spec/` are a clean room.** They are published, so nothing under them may carry the
   private working context they were authored in: no home-relative path other than the illustrative
   `~/work/`, no name of local-only tooling, no pointer to a gitignored folder, and no personal
   attribution. `tools/build.py` enforces this, so a slip fails the build rather than reaching a
   reader. If it fires, move the content rather than rewording to dodge the pattern.
9. **YAML hygiene.** Quote any string that contains a colon and a space, or that starts with a
   backtick, or YAML parses it as a mapping. Match the quoting style already in `data/tree-spec.yml`.

## Shapes

| Shape | Looks like | Schema |
|---|---|---|
| Sectioned spec | Normative rules about what the tool does, with decision tables | `structure/sectioned.schema.yml` |
| Tracker | Grouped items, each carrying a status, a backing tag, or an owning doc | `structure/tracker.schema.yml` |
| Bespoke | A doc whose substance fits no shared shape | Its own `structure/<doc>.schema.yml` |

A thin `structure/<doc>.schema.yml` that `$ref`s a shared shape keeps the one-validator-per-source
convention intact while the shape itself lives once. A `$ref` between validators names the `.yml`
file, since nothing here is emitted to JSON.

Rules in the sectioned shape are `{name, description, check}`. `name` is the linter's stable rule id,
and `check` routes the rule to its enforcer: `static` for config as written, `resolved` for after the
cascade and tree build, `runtime` for live state, `none` for behavior or a definition that is not
enforced. A rule carries no machine-readable predicate.

## Adding or changing a source

1. Write or edit `data/<doc>.yml`. Give a new file the modeline
   `# yaml-language-server: $schema=../structure/<doc>.schema.yml` as its first line.
2. Write or reuse `structure/<doc>.schema.yml`.
3. Verify, and read the output:

```console
check-jsonschema --schemafile design/structure/<doc>.schema.yml design/data/<doc>.yml
python3 tools/build.py --check
yamllint --strict -c .yamllint .
```

## The source-only key

A key whose name starts with `_` is source-only and is stripped when
`spec/molecule-config.schema.yml` is emitted, at any depth. Notes, provenance, and the rationale for a
constraint go in a `_`-key or a YAML comment, neither of which reaches the artifact.
