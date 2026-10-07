# Two playbooks, single-config form

This is a synthetic example, written for this repo. It is a playbook project with two playbooks,
`playbooks/motd.yml` and `playbooks/hosts.yml`, each tested by its own Molecule scenario, and every
scenario declared in one root `molecule.yml`.

There is no scenario folder. A scenario is an entry in the root file, and every playbook it runs
lives in `playbooks/molecule/`. The two scenarios are independent, so they stay roots and share
their config through `defaults:`. Three stages are the same for both and are written once:

- `create.yml` starts one podman container per platform the scenario selects, with the `podman`
  CLI, and `destroy.yml` removes them. Each scenario gets its own container, `motd-instance` or
  `hosts-instance`.
- `converge.yml` is a single `import_playbook` of the playbook named for the scenario, read from
  `MOLECULE_SCENARIO_NAME`, so the `motd` scenario runs `playbooks/motd.yml`.

`verify` is the only stage that differs, because each playbook writes a different file. Each node
names its own `verify-<scenario>.yml`, which reads that file inside the container. Molecule's
built-in test sequence runs, idempotence included.

This example's `create.yml` passes `--no-hosts` to `podman run`. Podman otherwise mounts its own
`/etc/hosts` into the container, and the `hosts` playbook cannot replace a mounted file. The other
synthetic examples leave the flag out because nothing they test touches that file.

The platform image is `quay.io/fedora/fedora-toolbox:42` because the plain Fedora images carry no
Python. The `containers.podman` collection is needed for its connection plugin only. Paths in the
root file are relative to the project root, the folder the file sits in, and each reaches a
projected scenario file as `${MOLECULE_PROJECT_DIRECTORY}/playbooks/molecule/...`.

The converter projects this file into a top-level `molecule/` layout with `--scenarios-dir
molecule`. That projection, placed in a copy of this folder, passed `molecule test --all` on
Molecule 26.9.0, ansible-core 2.21.4 and containers.podman 1.21.0 against rootless podman 5.6.2,
with each playbook applied, idempotent and verified in its own container. It is a preset on the
converter page.
