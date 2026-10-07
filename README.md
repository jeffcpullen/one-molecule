# one-molecule: one molecule.yml for every scenario

Molecule spreads a project's test config across many files: a `molecule.yml` in every scenario
directory, a base `config.yml`, and `shared_state` when scenarios test against one environment.
This repository defines a single `molecule.yml` at the project root that carries all of it.

It is fully backwards compatible. Everything an existing project writes today has a place in the
one file, and the converter writes the one file back out as the per-scenario files today's
Molecule reads.

- [Documentation](https://jeffcpullen.github.io/one-molecule/): getting started, migrating, the explanation, and the full reference.
- [Converter](https://jeffcpullen.github.io/one-molecule/converter/): paste a single-file `molecule.yml` and see the per-scenario files today's Molecule needs.
- [Spec](spec/molecule-config.schema.yml): the single-file format, version 0.3.0.

This is a personal project. It is not a Molecule project proposal and does not represent the
position of the author's employer.

## The problem

Molecule has no scope larger than a single scenario. Anything shared across scenarios, whether
config, playbooks, platforms or an environment several scenarios test against, has nowhere to
live. So each scenario directory repeats most of the next one, shared settings go in a separate
base config, and shared setup needs `shared_state` and a scenario that must be named `default`.

## Many files become one

The `collection-shared-state` example is a collection with two roles that both write into one
application tree on one host. A `default` scenario builds the host and the tree, and each role
has a scenario that tests against it. Today's Molecule needs four files for that:

```text
extensions/molecule/
  config.yml                 shared_state: true
  default/molecule.yml
  app_config/molecule.yml
  app_users/molecule.yml
```

The single file says the same thing once:

```yaml
# molecule.yml  (project root)
---
platforms:
  - name: instance
    image: quay.io/fedora/fedora-toolbox:42

defaults:
  driver:
    name: default
  playbooks:
    converge: playbooks/molecule/converge.yml
    create: playbooks/molecule/create.yml
    destroy: playbooks/molecule/destroy.yml
  provisioner:
    name: ansible
    inventory:
      group_vars:
        all:
          ansible_connection: containers.podman.podman

scenarios:
  - name: default
    playbooks:
      create: playbooks/molecule/create-default.yml
      verify: playbooks/molecule/verify-default.yml
    scenario:
      test_sequence:
        - create
        - verify
        - destroy
    children:
      - name: app_config
        playbooks:
          verify: playbooks/molecule/verify-app_config.yml
      - name: app_users
        playbooks:
          verify: playbooks/molecule/verify-app_users.yml
```

Shared config sits once under `defaults:`, the platform sits once in the top-level catalog, and
each scenario names only what is its own. Nesting `app_config` and `app_users` under
`default`'s `children:` says what `shared_state: true` said. The converter writes this file back
as the four files above.

## Backwards compatible

Every part of today's layout has a place in the single file.

| Today | In the single file |
|---|---|
| A scenario directory's `molecule.yml` | An entry under `scenarios:`, with the same keys |
| A base `config.yml` | The top-level `defaults:` block |
| An inline platform list | The same list, or names from the catalog |
| `provisioner.playbooks` | `playbooks:`, a shorthand for it |
| A stage playbook in the scenario directory | Left unset, found by Molecule's default discovery |
| `shared_state: true` with a `default` scenario | A `default` root with the other scenarios as its children |
| The `--workers` flag | The flag, or a `workers` key in the file |

The keys on a scenario are Molecule's own, each validated by Molecule's own schema. A project
that keeps its scenario directories runs unchanged, `shared_state` included.

The single file also adds a few things today's layout has no place for: a platform defined once
and selected by name, inventory `host_vars` on that platform, and the `workers` cap committed
in the file. The converter turns each into ordinary scenario config, or names the flag to pass.

## The spec

`spec/molecule-config.schema.yml` is the authored source of the format, version 0.3.0, written
against Molecule v26.6.0. `tools/build.py` emits it as `generated/molecule-config.schema.json`,
published at its `$id`:

```text
https://raw.githubusercontent.com/jeffcpullen/one-molecule/v0.3.0/generated/molecule-config.schema.json
```

Each spec version is tagged `v<version>`. The [reference](design/docs/reference.md) states every
key in it.

## Examples

Four synthetic examples, written for this repository, each show one common layout on its own.
Each is the project itself in the single-file form, with its root file at
`examples/<name>/molecule.yml`, and each is a preset on the converter page.

| Example | Shape |
|---|---|
| `playbooks` | A playbook project with two independent scenarios |
| `roles` | Three standalone roles, one scenario each |
| `collection` | A collection with two roles, one scenario each |
| `collection-shared-state` | A collection whose scenarios test against one shared environment |

`examples/` also keeps upstream projects, each with its testing files copied from a pinned
upstream commit in `before/` and a converted root file in `after/`. `NOTICES.md` maps each one to
its source, commit and license.

## What is in here

The top-level folder says what may be edited by hand:

| Folder | |
|---|---|
| `design/` | The design corpus. `data/` is the design itself as YAML, `structure/` is the schemas that validate it, `docs/` is the written documentation |
| `spec/` | The authored source of the config schema, the deliverable of this work |
| `generated/` | Build output. Never edited by hand, produced by `tools/build.py` |
| `vendor/` | Upstream files kept as they are |

## Licensing

Every file keeps the license of the project it came from. Copied files retain their original
notices, and each example's `before/` carries its upstream `LICENSE`. Refactored files carry the
same license as their source and a line recording the change. Original material in this repo is
Apache-2.0, and `NOTICES.md` says exactly which files that covers. Full license texts are in
`LICENSES/`, and `NOTICES.md` maps every example to its upstream source, commit, and license.
