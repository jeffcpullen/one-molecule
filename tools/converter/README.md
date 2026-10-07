# Converter

Projects a single-config `molecule.yml` into the per-scenario `extensions/molecule/<name>/molecule.yml`
files today's Molecule reads, and lists what the projection could not carry. It runs as a command
and as a static web page published with the docs site under `converter/`.

It implements the latest released spec only, the version in `generated/molecule-config.schema.json`.
The page reads the version it names from that schema. Earlier versions are not selectable, because
their resolution rules differ and the examples it offers are written against the latest.

It converts in one direction only. Going from today's layout to the single file is the
parent-versus-defaults judgment in `design/docs/migrating.md`, which no tool makes.

## One source of truth

| File | Role |
|---|---|
| `project.py` | The projection. Standard library only. Key classes come from the schema's `x-class` annotations |
| `render.py` | YAML in and out, through PyYAML |
| `starter.py` | The starter file the page opens on: a live `defaults:` block and one live `integration_sample_filter` scenario that together project to the `molecule.yml` the ansible-creator collection scaffold generates, with every other key the spec declares commented out. Keys and notes come from the schema, and the sub-keys of Molecule's sections from Molecule's own schema |
| `cli.py` | Command line front end |
| `web/` | The page. Its JavaScript is interface only and holds no conversion rule. Both panes are CodeMirror 6 editors with YAML highlighting, loaded from esm.sh at the exact versions the import map in `index.html` pins |
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

## Layout

The projection assumes the content is a collection and places each scenario where the
ansible-creator collection scaffold does, `extensions/molecule/<name>/molecule.yml`, with shared
playbooks reached as `../utils/playbooks/`. A standalone role or a playbook project keeps its scenarios
in a top-level `molecule/` directory instead, and the tool does not offer that layout yet.

Paths are copied as written, so a path that names or climbs out of the scenarios directory keeps the
layout its author wrote it for. The openstack-systemd-service, osism-commons and dev-sec-hardening
presets come from projects with a top-level `molecule/` directory. openstack-systemd-service's
`../../tests/` playbook paths and the `molecule/<name>/` requirements paths in osism-commons and
dev-sec-hardening point where upstream's layout puts those files, not where `extensions/molecule/`
would.

## Coverage

Each directory under `fixtures/` is the expected projection of an example's single-file
`molecule.yml`, compared byte for byte. That file is `examples/<slug>/molecule.yml` for a synthetic
example and `examples/<slug>/after/molecule.yml` for an upstream one. Only fixture-covered examples
appear as presets on the page.

| Example | Covered | What it shows |
|---|---|---|
| collection | yes | Two flat roots sharing `defaults:`, shared stub playbooks reached in `playbooks/molecule/` |
| collection-shared-state | yes | A root that creates and two children, each child reported `lost` because today's Molecule has no parent edge |
| playbooks, roles | not yet | Their scenarios live in a top-level `molecule/` directory, a layout the tool does not offer yet |
| openstack-systemd-service | yes | Run `defaults:` merged under one scenario, playbook paths copied as written |
| osism-commons | yes | Two scenarios sharing one `defaults:` key, playbooks found by default discovery |
| dev-sec-hardening | yes | Seven scenarios sharing `defaults:`, two overriding only `test_sequence` |
| david-igou-armbian | yes | Catalog selections projected as `<scenario>-<catalog name>` platform entries |
| david-igou-routeros-configuration | no | The projection drops YAML comments, so the throwaway `chr_admin_password` would lose its inline `# notsecret` marker in every fixture file |
| the other five | not yet | |

A synthetic example has no `before/`, because its fixture is its per-scenario form. Each upstream
fixture was compared with upstream's `before/` scenario files, with any upstream base
`config.yml` merged under each scenario the way Molecule merges it. Every difference traces to a
choice the example's own `after/molecule.yml` makes, never to the tool:

- `scenario.name` is absent, because the scenario directory carries the name.
- armbian's `ansible.playbooks` entries are absent, because each names `<stage>.yml` in the
  scenario's own directory, which Molecule finds by default discovery.
- armbian's static `--inventory=inventory/` argument is replaced by the catalog.
- armbian's platform entries stand in for upstream's per-scenario `inventory/hosts.yml`. A catalog
  selection's instance is named `<scenario>-<catalog name>`, so only `bootstrap_armbian` and
  `pxelinux_render`, which declare inline platforms, keep upstream's host name `instance`.

A playbook path in the root file is relative to the node's scenario directory, as in Molecule
today, so the projection copies it as written.

Molecule v26.6.0 moves `provisioner.playbooks` into `ansible.playbooks` on load, so the
projection's `provisioner.playbooks` is equivalent to upstream's `ansible.playbooks`.

## What it does not check

The tool checks run, node and `defaults:` keys against the spec's own key lists. It does not validate values against
Molecule's per-key schema. The `check-jsonschema-examples` hook does that for the examples only.
Paths are copied as written and never checked against the tree. A null or empty-string value is
projected as written, and a list replaces the lower layer's list whole.
