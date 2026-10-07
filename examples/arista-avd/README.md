# arista.avd, single-config form

This is a proof of concept of a testing layout idea. It takes the real molecule scenario set from
`arista.avd` (pinned at commit `4d7cbccb0218d414a2cd2034b081d01b6768c487` on `devel`, copied verbatim
into `before/`) and shows it collapsed into one root `molecule.yml`.

## Changed

| | Before | After |
|---|---|---|
| Config and orchestration files | 32 | 1 |
| Scenario folders | 30 | 29 |
| Total lines | 914 | 285 |

The scenario folders stay. Each one still holds the stage playbooks and inventory upstream keeps
there, which Molecule finds by its default discovery relative to the scenario directory, so the
single file names a playbook only where upstream named one. The After count is the folders that
still hold a file once their `molecule.yml` is gone, taken from the upstream tree at the pinned
commit. Only `default` empties, because it holds nothing but its `molecule.yml`. `before/` copies
only the config, orchestration and lifecycle files, so most of those playbooks are not in it.

Three `example-single-dc-*` scenarios spell out Molecule's built-in `converge_sequence`, four lines
each. Upstream leaves it unset there, the shared `defaults:` sets one, and the config schema does not
accept the empty value the spec uses to clear a default.

The version fan-out (controller python and ansible-core) is not in `molecule.yml`. That axis lives with the outer caller, which is what `arista.avd` does today: its CI iterates the versions and calls the test tool as a plain caller. The single-config form carries the tree, the outer caller carries the grid.
