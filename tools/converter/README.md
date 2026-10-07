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
| `starter.py` | The starter file the page opens on: every key the spec declares, commented out, with one live scenario. Keys and notes come from the schema, and the sub-keys of Molecule's sections from Molecule's own schema |
| `cli.py` | Command line front end |
| `web/` | The page. Its JavaScript is interface only and holds no conversion rule |
| `stage_pages.py` | Copies the page, the two modules, the generated schema, the presets and the starter file into a directory, with a content-hash `build.json` the page loads every file under |

The page loads `project.py` and `render.py` into Pyodide and calls them. No conversion rule
exists in a second language.

## Run it

```text
python3 tools/converter/cli.py examples/openstack-systemd-service/after/molecule.yml
python3 tools/converter/cli.py <molecule.yml> --out <dir>
python3 tools/converter/cli.py --starter
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

| Example | Covered | What it shows |
|---|---|---|
| openstack-systemd-service | yes | Run `defaults:` merged under one scenario, playbook paths copied as written |
| osism-commons | yes | Two scenarios sharing one `defaults:` key, playbooks found by default discovery |
| dev-sec-hardening | yes | Seven scenarios sharing `defaults:`, two overriding only `test_sequence` |
| david-igou-armbian | yes | Catalog platform selections `unresolved` |
| david-igou-routeros-configuration | no | The projection drops YAML comments, so the throwaway `chr_admin_password` would lose its inline `# notsecret` marker in every fixture file |
| the other five | not yet | |

Each fixture was compared with upstream's `before/` scenario files, with any upstream base
`config.yml` merged under each scenario the way Molecule merges it. Every difference traces to a
choice the example's own `after/molecule.yml` makes, never to the tool:

- `scenario.name` is absent, because the scenario directory carries the name.
- armbian's `ansible.playbooks` entries are absent, because each names `<stage>.yml` in the
  scenario's own directory, which Molecule finds by default discovery.
- armbian's static `--inventory=inventory/` argument is replaced by the catalog.

A playbook path in the root file is relative to the node's scenario directory, as in Molecule
today, so the projection copies it as written.

Molecule v26.6.0 moves `provisioner.playbooks` into `ansible.playbooks` on load, so the
projection's `provisioner.playbooks` is equivalent to upstream's `ansible.playbooks`.

## What it does not check

The tool checks run, node and `defaults:` keys against the spec's own key lists. It does not validate values against
Molecule's per-key schema. The `check-jsonschema-examples` hook does that for the examples only.
Catalog platform selections have no projection yet, because the instance name a selection gets is an
open question in the design. Paths are copied as written and never checked against the tree. The
starter file lists no stage names under `playbooks`, because neither the spec's schema nor Molecule's
declares them as keys.
