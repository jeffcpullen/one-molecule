# The pattern: one top-level molecule.yml

Molecule discovers scenarios as directories today. Each scenario directory is expected to
carry its own converge and verify playbooks and its own config, so anything shared between
scenarios has to be duplicated, symlinked, or pulled in through a shim. Projects solve this
in many different ways, which is what the examples in this repo show.

The single-config layout removes the cause.

## One root file

A single `molecule.yml` at the project root holds:

- run-level defaults, which is what a base `config.yml` holds today,
- the scenario declarations, each a named entry rather than a directory,
- the parent and child edges between scenarios,
- the test matrix.

It carries config, not content. Playbooks stay playbooks. The file references them by path
through the existing `provisioner.playbooks` mapping, so referencing is behavior Molecule
already has.

## One shared playbooks folder

Shared converge, verify, create, and destroy playbooks live once under `playbooks/molecule/`,
and every scenario references the ones it needs. Written once, referenced by many, no copy.
Under the project's own `playbooks/` tree they are ordinary content: addressable by name and
lintable like any other playbook.

## Why the project root

The project root is the one location that exists identically for a collection, a role, and a
playbook project. `meta/` and `extensions/` exist only for collections, so anchoring there
would leave roles and playbook projects without a home and force a second location for them.

The full specification for this layout is in `reference.md`, and the reasoning behind it
is in `explanation.md`.
