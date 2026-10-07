# example.collection, single-config form

This is a synthetic example, written for this repo. It is a collection scaffolded with
ansible-creator 26.9.0 and given two roles, `motd` and `issue`, each tested by its own Molecule
scenario under `extensions/molecule/`, and every scenario declared in one root `molecule.yml`.

Only the files the test layout touches are kept: `galaxy.yml`, `meta/runtime.yml`, the roles and the
Molecule tree. The rest of the scaffold, including its sample plugins and the `integration_sample_filter`
scenario that tests them, is left out. `galaxy.yml` names Apache-2.0 in place of the scaffold's
`LICENSE` file.

The scaffold's per-scenario `molecule.yml` points `cleanup`, `destroy` and `prepare` at a shared
`noop.yml` under `extensions/molecule/utils/playbooks/`, a folder that exists because Molecule has no
shared home above a scenario. Here that playbook lives in `playbooks/molecule/` and is named once
under `defaults:`, alongside the scaffold's provisioner and sequence settings. The two roles share
config only, so they stay independent roots, and each node is just a name. Each scenario folder keeps
its own `converge.yml` and `verify.yml`, which Molecule finds by default discovery.

The stub playbooks are still there. The single file names the same three stubs the scaffold does,
just once, rather than asking whether a localhost scenario needs them at all.

The converter projects this file back into the scaffold's per-scenario layout. It is a preset on the
converter page.
