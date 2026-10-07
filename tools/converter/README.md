# Converter

Projects a single-config `molecule.yml` into the per-scenario `<scenarios directory>/<name>/molecule.yml`
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
| `project.py` | The projection, the referenced playbook paths and the start order. Standard library only. Key classes come from the schema's `x-class` annotations |
| `render.py` | YAML in and out, through PyYAML |
| `starter.py` | The starter file the page opens on: a live `defaults:` block and one live `integration_sample_filter` scenario that together project to the `molecule.yml` the ansible-creator collection scaffold generates, with every other key the spec declares commented out. Keys and notes come from the schema, and the sub-keys of Molecule's sections from Molecule's own schema |
| `cli.py` | Command line front end, and the example helpers the staging and the browser check share |
| `web/` | The page. Its JavaScript is interface only and holds no conversion rule. Both panes are CodeMirror 6 editors with YAML highlighting, loaded from esm.sh at the exact versions the import map in `index.html` pins |
| `stage_pages.py` | Copies the page, the two modules, the generated schema, the presets and the starter file into a directory, with a content-hash `build.json` the page loads every file under. Each preset carries the text of every referenced playbook that exists in its example |

The page loads `project.py` and `render.py` into Pyodide and calls them. No conversion rule
exists in a second language.

## Run it

```text
python3 tools/converter/cli.py examples/openstack-systemd-service/after/molecule.yml
python3 tools/converter/cli.py <molecule.yml> --out <dir>
python3 tools/converter/cli.py <molecule.yml> --scenarios-dir molecule --out <dir>
python3 tools/converter/cli.py <molecule.yml> --order --workers 2
python3 tools/converter/cli.py --starter
python3 -m unittest discover -s tools/converter -p 'test_*.py' -v
```

`--order` prints the step each scenario starts at instead of the projection. With no `--workers`
there is no limit on parallel execution and it prints `workers: no limit`. `--workers N` caps it and
prints the value as given.

`browser_smoke.py` serves nothing itself. Stage the page, serve the directory, and point it at the
URL. It needs Playwright with Chromium, as in `.github/workflows/converter.yml`. The pages workflow
runs the same check against the deployed site after every deploy. `--shots <dir>` also saves
full-page screenshots of the collection-shared-state preset and of the roles preset with no workers
limit and at workers 1.

## The page

Each side has a column of file buttons to the left of its code area, with the selected file's path
above the code. A shared directory is shown once as a heading over its files.

| Side | Lists |
|---|---|
| Proposed layout | `molecule.yml`, selected by default and editable, then every playbook it references |
| Today's layout | The projected files, then the same referenced playbooks |

A node's referenced playbooks are its `playbooks` and `provisioner.playbooks` values merged over
those under `defaults:`, the way the projection merges them, so a stage the node sets itself hides
the `defaults:` path for that stage. Each is resolved from `<scenarios directory>/<node name>/` to a
path from the project root, for every node, children included. A playbook opens read-only.

A referenced path is available only when the loaded preset ships it. A synthetic preset ships every
referenced file that exists under `examples/<slug>/`. Upstream presets do not ship their playbooks,
so their references show as not available. Any other path is marked not available, and selecting it
says the file is not part of this input. Selecting `molecule.yml` again returns to the editor with
any edits kept.

## Start order

The start order shows the step at which each scenario begins, one column per step and one block per
scenario, with a line from each parent to its children. It follows the scheduling in
`design/docs/reference.md`, without the cleanup and destroy units:

- Each scenario takes one step.
- A child is ready once its parent has completed.
- Among nodes that share a parent, roots sharing the run, the lowest wave is ready first. A node is
  ready only once every sibling in a lower wave has completed its whole subtree.
- A wave the projection reports as an error, anything but an integer or an integral float, is
  ordered as wave 0.
- Workers is opt-in. Without it every ready scenario starts. With it, at most that many start per
  step, and ready scenarios beyond it wait, the earliest ready first, ties in list order.

The workers field starts empty, which means no limit. A whole number of at least 1 applies as a cap
and redraws the order at once. A value above the number of scenarios stays as typed and binds
nothing. Clearing the field returns to no limit. Any other entry is marked invalid and leaves the
last order in place. Loading a preset or the starter clears the field.

## Notices

| Kind | Means |
|---|---|
| `error` | The input breaks the spec, such as a key the spec does not declare |
| `unresolved` | The design does not decide the case yet, so the tool does not pick an answer |
| `lost` | The tree carries it, today's Molecule cannot, such as a parent edge or a wave |

## Layout

The projection places each scenario under a scenarios directory that `--scenarios-dir` and the page's
selector choose:

| Scenarios directory | For | Scenario file |
|---|---|---|
| `extensions/molecule` (default) | A collection, as the ansible-creator scaffold lays it out | `extensions/molecule/<name>/molecule.yml` |
| `molecule` | A standalone role or a playbook project | `molecule/<name>/molecule.yml` |

A tree maps onto Molecule's `shared_state` when it has one root named `default`, every other node is
a direct child of it, the root resolves at least one platform, the root's `scenario.test_sequence`,
when set, has both `create` and `destroy`, and no child selects platforms or sets its own `create` or
`destroy` playbook. The projection then writes a base config with `shared_state: true`, gives each
child the root's resolved platform entries, and reports no `lost` notice for the edges. The base
config lands where Molecule looks for it: `extensions/molecule/config.yml` for a collection, and
`.config/molecule/config.yml` at the projection root for the `molecule` layout, which must be the
project's VCS root. Any other tree with children keeps a `lost` notice per child that names the
condition that failed.

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
| collection | yes | Two flat roots sharing `defaults:` and one catalog platform, shared playbooks reached in `playbooks/molecule/` |
| collection-shared-state | yes | A `default` root that creates and two direct children, projected with `extensions/molecule/config.yml` setting `shared_state: true`, each child carrying the parent's `default-instance` platform entry, and no `lost` notice |
| roles | yes | Three flat roots under the `molecule/` layout, one shared converge naming the role by scenario |
| playbooks | yes | Two flat roots under the `molecule/` layout, one shared converge importing the playbook named by the scenario |
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
