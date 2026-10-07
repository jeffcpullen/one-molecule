# Getting started: one molecule.yml for a playbook project

This is a start-to-finish walk-through. You begin with one scenario in a single root
`molecule.yml` and grow it in four stages: one scenario, two independent scenarios, a platform
defined once, and a setup scenario the others test against. At every stage the
[converter](converter/) turns the file into the per-scenario files today's Molecule reads, and
you run those with Molecule as it is.

For the authoring surface, see [the pattern](the-pattern.md), and for every key, see the
[reference](reference.md). For why one file is less work than a directory per scenario, see the
[explanation](explanation.md).

## Before you start

You need Molecule, ansible-core, the `containers.podman` collection and podman. The scenarios
here run in podman containers on the `quay.io/fedora/fedora-toolbox:42` image, which carries the
Python Ansible needs on the target.

The project is a playbook project with one playbook to test, `playbooks/motd.yml`, which writes
`/etc/motd`. The test playbooks live under `playbooks/molecule/`. Copy `create.yml`,
`destroy.yml` and `converge.yml` from `examples/playbooks/playbooks/molecule/` in this
repository.

- `create.yml` starts one container per platform the scenario selects, and `destroy.yml`
  removes them.
- `converge.yml` imports the playbook named for the scenario, so a scenario called `motd` runs
  `playbooks/motd.yml`.

## Stage 1: one scenario

Start with the smallest thing that runs, one scenario and nothing else.

### The root file

Put one `molecule.yml` at the project root.

```yaml
# molecule.yml  (project root)
---
scenarios:
  - name: motd
    driver:
      name: default
    platforms:
      - name: motd-instance
        image: quay.io/fedora/fedora-toolbox:42
    provisioner:
      name: ansible
      inventory:
        group_vars:
          all:
            ansible_connection: containers.podman.podman
    playbooks:
      create: playbooks/molecule/create.yml
      converge: playbooks/molecule/converge.yml
      verify: playbooks/molecule/verify-motd.yml
      destroy: playbooks/molecule/destroy.yml
```

`scenarios` is the list of scenarios, and `motd` is the only one. Every key on it is a key
Molecule already takes in a scenario's `molecule.yml`. `playbooks` is a shorthand for
`provisioner.playbooks`, and each path is relative to the project root.

Write `playbooks/molecule/verify-motd.yml` to check the file the playbook writes, or copy it from
the same example.

### Convert it

Paste the file into the [converter](converter/) with the `molecule` scenarios directory, or run
it from a clone of this repository.

```
python3 tools/converter/cli.py molecule.yml --scenarios-dir molecule --out .
```

The converter writes one file, `molecule/motd/molecule.yml`, which is the scenario file Molecule
reads today.

```yaml
# molecule/motd/molecule.yml
---
driver:
  name: default
platforms:
  - name: motd-instance
    image: quay.io/fedora/fedora-toolbox:42
provisioner:
  name: ansible
  inventory:
    group_vars:
      all:
        ansible_connection: containers.podman.podman
  playbooks:
    create: ${MOLECULE_PROJECT_DIRECTORY}/playbooks/molecule/create.yml
    converge: ${MOLECULE_PROJECT_DIRECTORY}/playbooks/molecule/converge.yml
    verify: ${MOLECULE_PROJECT_DIRECTORY}/playbooks/molecule/verify-motd.yml
    destroy: ${MOLECULE_PROJECT_DIRECTORY}/playbooks/molecule/destroy.yml
```

Each playbook path now starts with `${MOLECULE_PROJECT_DIRECTORY}`, which Molecule fills in, so
the same path reaches the same file from any scenario directory.

### Run it

```
molecule test --all
```

Run it from the project root. Molecule runs `motd` through its usual sequence.

## Stage 2: two independent scenarios

Add a second playbook, `playbooks/hosts.yml`, which writes `/etc/hosts`, and a scenario to test
it. Two scenarios are two entries in `scenarios:`. Neither depends on the other.

The two share the driver, the connection and three of their playbooks. Writing those on each
scenario would repeat them, so lift them into a top-level `defaults:` block, which applies to
every scenario.

```yaml
# molecule.yml  (project root)
---
defaults:
  driver:
    name: default
  provisioner:
    name: ansible
    inventory:
      group_vars:
        all:
          ansible_connection: containers.podman.podman
  playbooks:
    create: playbooks/molecule/create.yml
    converge: playbooks/molecule/converge.yml
    destroy: playbooks/molecule/destroy.yml

scenarios:
  - name: motd
    platforms:
      - name: motd-instance
        image: quay.io/fedora/fedora-toolbox:42
    playbooks:
      verify: playbooks/molecule/verify-motd.yml
  - name: hosts
    platforms:
      - name: hosts-instance
        image: quay.io/fedora/fedora-toolbox:42
    playbooks:
      verify: playbooks/molecule/verify-hosts.yml
```

A key set directly on a scenario applies to that scenario only. A key under `defaults:` applies
to every scenario that does not set it. Mappings merge, so each scenario sets only
`playbooks.verify` and still receives the other three stages from `defaults:`.

Convert it again. The converter now writes `molecule/motd/molecule.yml` and
`molecule/hosts/molecule.yml`, each a complete scenario file with the `defaults:` keys merged
in. `molecule test --all` runs both.

## Stage 3: a platform defined once

Both scenarios still write the same platform, differing only in its name. Define it once in the
top-level `platforms:` catalog instead.

```yaml
# molecule.yml  (project root)
---
platforms:
  - name: instance
    image: quay.io/fedora/fedora-toolbox:42

defaults:
  driver:
    name: default
  provisioner:
    name: ansible
    inventory:
      group_vars:
        all:
          ansible_connection: containers.podman.podman
  playbooks:
    create: playbooks/molecule/create.yml
    converge: playbooks/molecule/converge.yml
    destroy: playbooks/molecule/destroy.yml

scenarios:
  - name: motd
    playbooks:
      verify: playbooks/molecule/verify-motd.yml
  - name: hosts
    playbooks:
      verify: playbooks/molecule/verify-hosts.yml
```

A root scenario with no `platforms:` selects the whole catalog, here one entry. Each selection
gets an instance named `<scenario name>-<catalog name>`, so `motd` still gets `motd-instance`
and `hosts` still gets `hosts-instance`. The converted files are the same as in Stage 2.

This is the file in `examples/playbooks/`, apart from the `verifier` key that example also sets.

## Stage 4: a setup scenario the others test against

So far each scenario stands up its own container. Sometimes several scenarios need to test
against one environment that a setup scenario builds. Today that is Molecule's
`shared_state: true`, where a scenario named `default` builds the environment and every other
scenario reuses it.

In the single file you write that relationship by nesting. `default` is a root, and the
scenarios that test against it go under its `children:`.

```yaml
# molecule.yml  (project root)
---
platforms:
  - name: instance
    image: quay.io/fedora/fedora-toolbox:42

defaults:
  driver:
    name: default
  provisioner:
    name: ansible
    inventory:
      group_vars:
        all:
          ansible_connection: containers.podman.podman
  playbooks:
    create: playbooks/molecule/create.yml
    converge: playbooks/molecule/converge.yml
    destroy: playbooks/molecule/destroy.yml

scenarios:
  - name: default
    playbooks:
      verify: playbooks/molecule/verify-default.yml
    scenario:
      test_sequence:
        - create
        - verify
        - destroy
    children:
      - name: motd
        playbooks:
          verify: playbooks/molecule/verify-motd.yml
      - name: hosts
        playbooks:
          verify: playbooks/molecule/verify-hosts.yml
```

`default` selects the whole catalog and gets `default-instance`. The children select no
platforms, so they share their parent's instance. `default` has no playbook of its own to
converge, so its `test_sequence` is create, verify and destroy. Write `verify-default.yml` to
check the container is up.

Convert it. The converter writes `.config/molecule/config.yml` with `shared_state: true`, and
three scenario files, `molecule/default/molecule.yml`, `molecule/motd/molecule.yml` and
`molecule/hosts/molecule.yml`. Each child's file carries the parent's `default-instance`
platform entry, so its inventory holds the parent's host. The base config sits at the project
root, which must be the project's version-control root for Molecule to find it.

Under `shared_state`, Molecule runs `default`'s `create` and `destroy` once around the whole
run, and the other scenarios reuse what it built. The children inherit `create` and `destroy`
from `defaults:`, but Molecule runs those two stages only for `default`.

Use a parent only when the children cannot run without what it builds. Scenarios that only
repeat the same config stay roots and share it through `defaults:`, as in Stage 2.

The `collection-shared-state` example is this shape in a collection.

## Where to go next

For every key and how a value resolves, read the [reference](reference.md). For how the root
file is laid out, read [the pattern](the-pattern.md). For why one file is less work, read the
[explanation](explanation.md). To convert an existing project, read [migrating](migrating.md).
