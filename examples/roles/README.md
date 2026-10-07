# Three roles, single-config form

This is a synthetic example, written for this repo. It is a repository of three standalone roles,
`motd`, `issue` and `profile`, each tested by its own Molecule scenario, and every scenario declared
in one root `molecule.yml` at the repository root.

Today each role would carry its own `roles/<role>/molecule/default/` folder with a `molecule.yml`,
a `converge.yml`, a `verify.yml`, and whatever create and destroy playbooks its driver needs. Here
the roles carry no test folders and there is no scenario folder anywhere. A scenario is an entry in
the root file, and every playbook it runs lives in `playbooks/molecule/`.

The three roles are independent, so they stay roots and share their config through `defaults:`.
Three stages are the same for all of them and are written once:

- `create.yml` starts one podman container per platform the scenario selects, with the `podman`
  CLI, and `destroy.yml` removes them. Each scenario gets its own container, such as
  `motd-instance`.
- `converge.yml` is a single `include_role` on the scenario name, read from
  `MOLECULE_SCENARIO_NAME`. A scenario is named for the role it tests, so one play applies the
  right role in each. `defaults:` sets `ANSIBLE_ROLES_PATH` to the project's `roles/` folder so the
  short name resolves.

`verify` is the only stage that differs, because each role writes a different file. Each node names
its own `verify-<scenario>.yml`, which reads that file inside the container. Molecule's built-in
test sequence runs, idempotence included.

The platform image is `quay.io/fedora/fedora-toolbox:42` because the plain Fedora images carry no
Python. The `containers.podman` collection is needed for its connection plugin only. Paths in the
root file are relative to each scenario's folder, `molecule/<name>/`, which is why they climb two
levels to reach `playbooks/molecule/`.

The converter projects this file into a top-level `molecule/` layout with `--scenarios-dir
molecule`. That projection, placed in a copy of this folder, passed `molecule test --all` on
Molecule 26.9.0, ansible-core 2.21.4 and containers.podman 1.21.0 against rootless podman 5.6.2,
with each role applied, idempotent and verified in its own container. It is a preset on the
converter page.
