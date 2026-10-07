# example.collection, single-config form

This is a synthetic example, written for this repo. It is a collection scaffolded with
ansible-creator 26.9.0 and given two roles, `motd` and `issue`, each tested by its own Molecule
scenario, and every scenario declared in one root `molecule.yml`.

Only the files the test layout touches are kept: `galaxy.yml`, `meta/runtime.yml`, the roles, the
root `molecule.yml` and `playbooks/molecule/`. There is no `extensions/molecule/` folder. A
scenario is an entry in the root file, and every playbook it runs is named there. `galaxy.yml`
names Apache-2.0 in place of the scaffold's `LICENSE` file.

The two roles are independent, so they stay roots and share their config through `defaults:`.
Three stages are the same for both and are written once:

- `create.yml` starts one podman container per platform the scenario selects, with the `podman`
  CLI, and `destroy.yml` removes them. A root that names no platforms gets the whole catalog, here
  one entry, so each scenario gets its own container, `motd-instance` or `issue-instance`.
- `converge.yml` is a single `include_role` on `example.collection.` plus the scenario name, read
  from `MOLECULE_SCENARIO_NAME`. A scenario is named for the role it tests, so one play applies
  the right role in each.

`verify` is the only stage that differs, because each role writes a different file. Each node
names its own `verify-<scenario>.yml`, which reads that file inside the container. Molecule's
built-in test sequence runs, idempotence included.

The platform image is `quay.io/fedora/fedora-toolbox:42` because the plain Fedora images carry no
Python, which Ansible needs on the target. The `containers.podman` collection is needed for its
connection plugin only. Paths in the root file are relative to the project root, the folder the
file sits in, and each reaches a projected scenario file as
`${MOLECULE_PROJECT_DIRECTORY}/playbooks/molecule/...`.

The converter projects this file into the scaffold's per-scenario layout. That projection, placed in
a copy of this folder at `ansible_collections/example/collection/`, passed `molecule test --all` on
Molecule 26.9.0, ansible-core 2.21.4 and containers.podman 1.21.0 through the podman 5.6.2 client
against a rootless podman 5.8.7 service, with each role applied, idempotent and verified in its own
container. It is a preset on the converter page.
