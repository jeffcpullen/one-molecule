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
| `starter.py` | The starter file the page opens on: a live `defaults:` block and one live `integration_sample_filter` scenario that together project to the `molecule.yml` the ansible-creator collection scaffold generates, its playbook paths written from the project root, with every other key the spec declares commented out. Keys and notes come from the schema, and the sub-keys of Molecule's sections from Molecule's own schema |
| `cli.py` | Command line front end, and the example helpers the staging and the browser check share |
| `web/` | The page. Its JavaScript is interface only and holds no conversion rule. Both panes are CodeMirror 6 editors with YAML highlighting, loaded from esm.sh at the exact versions the import map in `index.html` pins |
| `stage_pages.py` | Copies the page, the two modules, the generated schema, the presets and the starter file into a directory, with a content-hash `build.json` the page loads every file under. Each preset carries the text of every referenced playbook that exists in its example |

The page loads `project.py` and `render.py` into Pyodide and calls them. No conversion rule
exists in a second language.

## Run it

```text
python3 tools/converter/cli.py examples/collection/molecule.yml
python3 tools/converter/cli.py <molecule.yml> --out <dir>
python3 tools/converter/cli.py <molecule.yml> --scenarios-dir molecule --out <dir>
python3 tools/converter/cli.py <molecule.yml> --order --workers 2 --destroy never
python3 tools/converter/cli.py --starter
python3 -m unittest discover -s tools/converter -p 'test_*.py' -v
```

`--order` prints the step each scenario starts at instead of the projection. The cap on scenarios in
flight is the file's `workers` key, else 1, the default the spec and Molecule share. `--workers` takes
what Molecule's flag takes, an integer of at least 1, `cpus` or `cpus-1`, and overrides the file. The
first line prints the cap and, unless it is the default, where it came from. `cpus` counts the CPUs
of the machine the command runs on. `--destroy` takes Molecule's `always` or `never` and feeds only
the workers check below.

`browser_smoke.py` serves nothing itself. Stage the page, serve the directory, and point it at the
URL. It needs Playwright with Chromium, as in `.github/workflows/converter.yml`. The pages workflow
runs the same check against the deployed site after every deploy. `--shots <dir>` also saves
full-page screenshots of the collection-shared-state preset and of the roles preset at the default of
1 worker and at workers 3.

## The page

Each side has a column of file buttons to the left of its code area, with the selected file's path
above the code. A shared directory is shown once as a heading over its files.

| Side | Lists |
|---|---|
| Proposed layout | `molecule.yml`, selected by default and editable, then every playbook it references |
| Today's layout | The projected files, then the same referenced playbooks |

A node's referenced playbooks are its `playbooks` and `provisioner.playbooks` values merged over
those under `defaults:`, the way the projection merges them, so a stage the node sets itself hides
the `defaults:` path for that stage. Each is resolved from the project root, the folder the root
file sits in, for every node, children included, so the paths are the same in both layouts. A
playbook opens read-only.

A referenced path is available only when the loaded preset ships it. A preset ships every
referenced file that exists under `examples/<slug>/`. Any other path, such as one named in typed
input, is marked not available, and selecting it says the file is not part of this input. Selecting `molecule.yml` again returns to the editor with
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
- At most `workers` scenarios start per step, and ready scenarios beyond it wait, the earliest ready
  first, ties in list order. The cap is 1 unless the file's `workers` key or the field sets it.

The workers field starts empty, and its placeholder shows the cap in force: the file's `workers`
value, with `cpus` counted from the browser's reported CPU count, else 1. The note beside it says
which. A whole number of at least 1 overrides it, as `--workers` overrides the key, and redraws the
order at once. A value above the number of scenarios stays as typed and binds nothing. Clearing the
field returns to the file's value or 1. Any other entry is marked invalid and leaves the last order
in place. The destroy selector stands for Molecule's `--destroy` and feeds only the workers check.
Loading a preset or the starter clears the field and sets destroy back to `always`.

Today's Molecule reads the cap only from `--workers`, so a `workers` key in the file is reported
`lost` with the flag to pass. A cap above 1 is reported `unsupported` with the `molecule` scenarios
directory, which stands for a project without a `galaxy.yml`, and together with destroy `never`,
because Molecule rejects `--workers` above 1 in both cases.

## Notices

| Kind | Means |
|---|---|
| `error` | The input breaks the spec, such as a key the spec does not declare |
| `unresolved` | The design does not decide the case yet, so the tool does not pick an answer |
| `lost` | The tree carries it, today's Molecule cannot, such as a parent edge or a wave |
| `unsupported` | Today's Molecule rejects the combination at run time, such as workers above 1 outside a collection |

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

A relative `playbooks` path in the root file resolves against the project root, as spec 0.3.0
states, so the projection writes it into each scenario file as
`${MOLECULE_PROJECT_DIRECTORY}/<path>`, which Molecule fills in on each scenario's own read. The
path after the prefix is kept as written, a climb above the root included. An absolute path, and a
path that already starts with a `$` variable such as `${MOLECULE_PROJECT_DIRECTORY}`, is copied as
written, because the orchestrator passes Molecule's `${VAR}` through untouched. The projected files
therefore run from the project root, or from anywhere with `MOLECULE_PROJECT_DIRECTORY` exported.

## Coverage

Each directory under `fixtures/` is the expected projection of an example's single-file
`molecule.yml`, compared byte for byte. That file is `examples/<slug>/molecule.yml`, and only the
synthetic examples are covered. Every fixture-covered example appears as a preset on the page.

| Example | Covered | What it shows |
|---|---|---|
| collection | yes | Two flat roots sharing `defaults:` and one catalog platform, shared playbooks reached in `playbooks/molecule/` |
| collection-shared-state | yes | A `default` root that creates and two direct children, projected with `extensions/molecule/config.yml` setting `shared_state: true`, each child carrying the parent's `default-instance` platform entry, and no `lost` notice |
| roles | yes | Three flat roots under the `molecule/` layout, one shared converge naming the role by scenario |
| playbooks | yes | Two flat roots under the `molecule/` layout, one shared converge importing the playbook named by the scenario |

A synthetic example has no `before/`, because its fixture is its per-scenario form. The upstream
examples under `examples/` are not converter fixtures or presets.

A playbook path in the root file is relative to the project root, so a stage playbook particular to
one scenario is reached as `extensions/molecule/<name>/<stage>.yml` or `molecule/<name>/<stage>.yml`,
or left unset for Molecule's default discovery to find in the scenario directory.

Molecule v26.6.0 moves `provisioner.playbooks` into `ansible.playbooks` on load, so the
projection's `provisioner.playbooks` is equivalent to an `ansible.playbooks` block.

## What it does not check

The tool checks run, node and `defaults:` keys against the spec's own key lists. It does not validate values against
Molecule's per-key schema. The `check-jsonschema-examples` hook does that for the examples only.
A referenced path is never checked against the tree, beyond showing whether the loaded preset ships
it. Only `playbooks` paths are rewritten, because the spec's resolution rule names `playbooks` only. A null or empty-string value is
projected as written, and a list replaces the lower layer's list whole.
