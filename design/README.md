# The design corpus

Where molecule scenario orchestration should be aiming, and the milestones that get there without
rework. The corpus is data, not prose pages. Nothing here is rendered and nothing here is generated.

Start with `data/target.yml` for the aim, then `data/open-questions.yml` for what is still undecided,
then the file that owns the area you are touching.

## The split

| Folder | Holds | Editable by hand |
|---|---|---|
| `data/` | The design sources, one YAML file per subject. This is the corpus | Yes |
| `structure/` | One validator per source, plus the shared `sectioned` and `tracker` shapes | Yes |
| `docs/` | The Diataxis documentation set, a user-altitude projection of the corpus | Yes, by its own process |

Two folders elsewhere in the repo complete the picture, and neither is hand-edited:

| Folder | Holds | Editable by hand |
|---|---|---|
| `../generated/` | `molecule-config.schema.json`, emitted from `../spec/molecule-config.schema.yml` | No |
| `../vendor/` | `molecule.json`, vendored from upstream molecule | No, re-vendor instead |

`../spec/molecule-config.schema.yml` is the authored source of the deliverable JSON Schema and is
edited by hand like anything under `data/`.

## Reading a source

Each `data/<doc>.yml` carries a `yaml-language-server` modeline on its first line naming its
validator, so an editor offers completion and flags a violation as you type. The validators are
authored in YAML and are never emitted to JSON.

Most sources use the shared sectioned shape: a titled document of sections, each carrying atomic
rules and decision tables. The registers (`rejected-ideas`, `open-questions`, `interfaces`, `naming`,
`target`) carry their own bounded shapes. `AUTHORING.md` is the standard a new or edited source
follows.

## Validate and regenerate

Validate one source against its validator:

```console
check-jsonschema --schemafile design/structure/<doc>.schema.yml design/data/<doc>.yml
```

Regenerate the one generated file, and run the corpus linters:

```console
python3 tools/build.py            # write generated/molecule-config.schema.json
python3 tools/build.py --check    # exit 1 if it is stale or a linter fails
```

Everything above runs from the repo root through `pre-commit`, which also lints YAML with the repo
`.yamllint` and validates the `after/` example configs against the generated schema.
