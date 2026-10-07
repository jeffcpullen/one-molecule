# Reference: the single top-level molecule.yml

The lookup spec for the single-file `molecule.yml`, version 0.3.0. It states what each key is
and how a value resolves. For the authoring surface, read [the pattern](the-pattern.md). For a
guided build, read [getting started](getting-started.md). For converting an existing project,
read [migrating](migrating.md). For the reasoning, read the [explanation](explanation.md).

The spec is `spec/molecule-config.schema.yml` in the repository, published as this JSON schema.

```text
https://raw.githubusercontent.com/jeffcpullen/one-molecule/v0.3.0/generated/molecule-config.schema.json
```

It is written against Molecule v26.6.0, and each Molecule key in the file is validated by
Molecule's own schema for that key.

Molecule does not read the single file itself. The [converter](converter/) turns it into the
per-scenario files today's Molecule reads, and Molecule runs those as it runs any project.

## The root file

One `molecule.yml` at the project root holds every scenario and the config they share. A
scenario is a named entry in that file, not a directory. The file carries config, never
playbook content. Playbooks are referenced by path.

`scenarios` is the one required key. A key the spec does not declare fails validation, at
every level of the file.

A project that keeps its scenario directories runs unchanged. The single file is a second way
to declare the same scenarios, and Molecule's `shared_state` keeps its meaning in a project
that stays in directories.

## Top-level keys

The top level of the file is the run.

| Key | Class | What it is |
|---|---|---|
| `workers` | run-only | The cap on scenarios in flight |
| `platforms` | run-only | The platform catalog, each platform defined once by name |
| `defaults` | reserved structural | Config that applies to every scenario |
| `scenarios` | reserved structural | The list of root scenarios. Required, with at least one entry |

A run-only key belongs to the run and never sits on a scenario.

### workers

The number of scenarios in flight at once.

| Value | Meaning |
|---|---|
| an integer of at least 1 | That many scenarios |
| `cpus` | One per CPU |
| `cpus-1` | One per CPU, less one |

- The default is 1.
- The `--workers` flag overrides the key.
- A value above 1 needs a collection, a project with a `galaxy.yml`.
- A value above 1 is rejected together with `--destroy=never`, checked at run time.

Today's Molecule takes the cap only from `--workers`. The converter reports a `workers` key as
`lost` and names the flag to pass instead.

### platforms (the catalog)

The top-level `platforms:` is the catalog. Each entry is a Molecule platform entry, written
once and identified by `name`.

| Key | What it is |
|---|---|
| `name` | Required. The catalog identity a scenario selects. Unique across the catalog |
| `host_vars` | Inventory host variables for every instance made from this entry |
| any other key | Molecule's own platform keys, as in an inline platform entry |

A scenario's own `platforms:` is a selection. Each item is a catalog name, or an inline
platform object written as Molecule takes it today.

- A root scenario with no `platforms:` selects the whole catalog.
- A child selects none of its own and shares its parent's instances.
- A selected entry reaches the scenario's platforms as written, apart from its `name` and its
  `host_vars`.
- A selection's instance name is `<scenario name>-<catalog name>`. A root `motd` selecting the
  entry `instance` gets an instance named `motd-instance`.
- An inline platform keeps its `name` exactly as written.
- A catalog name and an inline platform name that match in one run is an error.
- `platforms` is permissive. Absent or empty is valid, and it is used only by a scenario that
  creates its own instances.

The catalog removes repeated definitions, not creation. Each scenario's own `create` playbook
still stands up the platforms it selects.

`host_vars` on an entry reaches each selecting scenario as `provisioner.inventory.host_vars`
under the instance name, never as a platform key. A scenario's own
`provisioner.inventory.host_vars` for that instance merges with it, and the scenario's value
wins where both set a variable. A child that shares its parent's instances receives the
`host_vars` the parent's catalog entries set for them.

### defaults

A sparse overlay of Molecule scenario keys. It holds any subset of the
[config keys](#config-keys), none required, and it is not a complete scenario. A key under
`defaults:` applies to every scenario that does not set the same key itself.

### scenarios

The list of root scenarios. Roots run in `wave` order, and in list order within a wave. List
order is the order a serial run takes and the order the `--workers` scheduler submits.

## Scenario keys

Every entry under `scenarios:` and under `children:` is a scenario, also called a node when it
is read as part of a tree.

| Key | Class | What it is |
|---|---|---|
| `name` | node-intrinsic | Required. The scenario's identity, selected by `-s`. Unique across the run |
| `wave` | node-intrinsic | An integer, default 0. The ordering tier among nodes that share a parent, roots included |
| `children` | reserved structural | The child scenarios. Nesting under `children:` is the parent edge |
| any config key | config | Applies to this scenario only |

### Config keys

A config key sits on a scenario, where it applies to that scenario only, or under the top-level
`defaults:`, where it applies to every scenario. Each value is validated by Molecule's own
schema for that key.

| Key | Note |
|---|---|
| `playbooks` | A shorthand for `provisioner.playbooks` (see [playbooks](#playbooks)) |
| `driver` | Usually set on the scenario that creates instances, so it is not handed to children |
| `platforms` | A selection of catalog names, or inline platform objects |
| `provisioner` | Molecule's own key |
| `verifier` | Molecule's own key |
| `dependency` | Molecule's own key |
| `ansible` | Molecule's own key |
| `scenario` | Molecule's own key, such as `test_sequence` |
| `lint` | Molecule's own key |
| `log` | Molecule's own key |
| `prerun` | Molecule's own key |
| `role_name_check` | Molecule's own key |

Molecule's `shared_state` is not a key in the single file. A tree declares what it stood for
(see [The tree](#the-tree)).

### playbooks

One playbook path per stage. Any other key under `playbooks:` fails validation.

| Stage | The playbook that |
|---|---|
| `create` | Creates the scenario's instances |
| `prepare` | Prepares the instances before converge |
| `converge` | Applies the content under test |
| `side_effect` | Applies a side effect before verify |
| `verify` | Verifies the instances |
| `cleanup` | Cleans up before destroy |
| `destroy` | Destroys the scenario's instances |

A value is a file path. A stage the scenario leaves unset is found in the scenario's own
directory by Molecule's default discovery. By convention `create` and `destroy` sit on the
scenario that creates, so a parent does not hand creation to its children.

## Scope and precedence

Config is placed in one of two spots, and the spot is the scope.

| Placement | Applies to |
|---|---|
| Directly on a scenario (a bare key) | That scenario only. It never cascades |
| Under the top-level `defaults:` | Every scenario that does not set the key bare |

A key resolves for a scenario in this order, highest first:

1. The scenario's bare key.
2. The key under `defaults:`.
3. Molecule's built-in default.

Across every input, the order is the CLI, then the environment, then the two layers above,
then the built-in default.

- A key is a key path, not only a top-level key. A scenario that sets `playbooks.verify` still
  receives `playbooks.converge` from `defaults:`.
- Mappings deep-merge across the layers.
- A list replaces the lower layer's list whole.
- A null or empty-string value is an ordinary value.

## Paths

| Path | How it resolves |
|---|---|
| A relative `playbooks` path | Against the project root, the folder the root file sits in |
| A `playbooks` path that is absolute or starts with `${` | As written |
| Any other path-valued key | Unchanged. Molecule resolves it as it does today |

A relative `playbooks` path reaches each scenario's file as
`${MOLECULE_PROJECT_DIRECTORY}/<path>`, which Molecule fills in when it reads that file. The
projected files therefore run from the project root, or from anywhere with
`MOLECULE_PROJECT_DIRECTORY` exported.

## The tree

A scenario nested under another's `children:` is its child. The nesting is the edge, and there
is no `parent:` key.

- A root is an entry directly under `scenarios:`, a scenario with no parent.
- A child has exactly one parent.
- A child shares its parent's instances, beginning from the parent's inventory.
- A child whose parent is not standing has the parent created first.
- Sharing is within a tree only. There is no sharing between trees.
- `wave` orders nodes that share a parent, and roots, which share the run as their parent.

### The tree today's Molecule runs

The tree is how the single file writes Molecule's `shared_state`. Today the setup scenario must
be named `default`, and `shared_state: true` in a shared base config makes every other scenario
reuse what `default` built. In the single file, `default` is a root and the scenarios that test
against it are its children.

The converter writes a tree as `shared_state` when all of these hold:

- There is one root, named `default`.
- Every other scenario is a direct child of it.
- The root resolves at least one platform.
- The root's `scenario.test_sequence`, when set, includes both `create` and `destroy`.
- No child selects platforms or sets its own `create` or `destroy` playbook.

It then writes a base config with `shared_state: true` and gives each child the root's resolved
platform entries. The base config goes to `extensions/molecule/config.yml` for a collection,
and to `.config/molecule/config.yml` at the project root for the `molecule/` layout, which must
be the project's version-control root.

Today's Molecule has no form for any other tree shape or for `wave`. The converter reports each
as a `lost` notice that names the condition that failed. The `collection-shared-state` example
is a working tree of this shape.

## What the converter writes for today's Molecule

Every part of today's per-scenario layout has a place in the single file, and the converter
writes each one back.

| Today's layout | In the single file |
|---|---|
| A base `config.yml` | The top-level `defaults:` |
| A scenario directory's `molecule.yml` | An entry under `scenarios:`, its keys bare |
| The scenario directory's name | `name:` |
| An inline platform list | The same list on the scenario, or catalog names |
| `provisioner.playbooks` | `playbooks:`, the shorthand for it |
| A stage playbook in the scenario directory | The stage left unset, found by default discovery |
| `shared_state: true` with a `default` scenario | A `default` root with the other scenarios as children |
| The `--workers` flag | The flag, or the `workers` key |

The converter places each scenario under a scenarios directory.

| Scenarios directory | For |
|---|---|
| `extensions/molecule/<name>/molecule.yml` | A collection |
| `molecule/<name>/molecule.yml` | A standalone role or a playbook project |

What the converter writes for keys that only the single file has:

| In the single file | In the scenario's file |
|---|---|
| A catalog selection | A platform entry named `<scenario name>-<catalog name>` |
| A catalog entry's `host_vars` | `provisioner.inventory.host_vars` under the instance name |
| A relative `playbooks` path | `${MOLECULE_PROJECT_DIRECTORY}/<path>` |
| The `workers` key | Nothing. Reported `lost`, with the `--workers` value to pass |

## Glossary

| Term | Means exactly |
|---|---|
| **Scenario** | One environment, one converge, one verify, one state. The base unit |
| **Node** | A scenario considered as a member of a tree |
| **Root** | A node with no parent, an entry directly under `scenarios:` |
| **Parent / child** | The edge declared by nesting under `children:`. A dependency, not configuration inheritance |
| **Tree** | A root scenario and everything nested under it |
| **Standing** | A node whose environment is up and converged, so it needs no work |
| **Bare key** | A config key placed directly on a scenario, applying to it alone |
| **Defaults** | Configuration inheritance through the `defaults:` block |
| **Platform catalog** | The top-level `platforms:`, each entry defined once and selected by name |
