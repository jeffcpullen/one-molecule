# Converter

Projects a single-config `molecule.yml` (spec 0.1.0) into the per-scenario `molecule/<name>/molecule.yml`
files today's Molecule reads, and lists what the projection could not carry. It runs as a command
and as a static web page published with the docs site under `converter/`.

It converts in one direction only. Going from today's layout to the single file is the
parent-versus-defaults judgment in `design/docs/migrating.md`, which no tool makes.

## One source of truth

| File | Role |
|---|---|
| `project.py` | The projection. Standard library only. Key classes come from the schema's `x-class` annotations |
| `render.py` | YAML in and out, through PyYAML |
| `cli.py` | Command line front end |
| `web/` | The page. Its JavaScript is interface only and holds no conversion rule |
| `stage_pages.py` | Copies the page, the two modules, the generated schema and the presets into a directory, with a content-hash `build.json` the page loads every file under |

The page loads `project.py` and `render.py` into Pyodide and calls them. No conversion rule
exists in a second language.

## Run it

```text
python3 tools/converter/cli.py examples/openstack-systemd-service/after/molecule.yml
python3 tools/converter/cli.py <molecule.yml> --out <dir>
python3 -m unittest discover -s tools/converter -p 'test_*.py' -v
```

`browser_smoke.py` serves nothing itself. Stage the page, serve the directory, and point it at the
URL. It needs Playwright with Chromium, as in `.github/workflows/converter.yml`. The pages workflow
runs the same check against the deployed site after every deploy.

## Notices

| Kind | Means |
|---|---|
| `error` | The input breaks the spec, such as a key the spec does not declare |
| `unresolved` | The design does not decide the case yet, so the tool does not pick an answer |
| `lost` | The tree carries it, today's Molecule cannot, such as a parent edge or a wave |

## Coverage

Each directory under `fixtures/` is the expected projection of `examples/<slug>/after/molecule.yml`,
compared byte for byte. Only fixture-covered examples appear as presets on the page.

| Example | Covered |
|---|---|
| openstack-systemd-service | yes |

The openstack fixture differs from upstream's `before/molecule/default/molecule.yml` in two places
only. The three playbook paths lack upstream's `../../` prefix, because the spec does not say what a
path in the root file is relative to, and the tool reports that as `unresolved`. `scenario.name` is
absent, because the scenario directory carries the name.

## What it does not check

The tool checks run, node and `defaults:` keys against the spec's own key lists. It does not validate values against
Molecule's per-key schema. The `check-jsonschema-examples` hook does that for the examples only.
Catalog platform selections have no projection yet, because the instance name a selection gets is an
open question in the design.
