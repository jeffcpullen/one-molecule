# one-molecule: one layout for scenario testing

Real Ansible projects, refactored to a single top-level `molecule.yml`. This repository is a
proof of concept for that idea.

This is a personal project. It is not a Molecule project proposal and does not represent the
position of the author's employer.

## The problem

Molecule has no scope larger than a single scenario. Anything shared across scenarios,
whether config, playbooks, or provisioning, has nowhere to live, so every project invents
its own way to avoid copying that shared material into each scenario directory. Each
project lands somewhere different.

This repo collects recognizable, community-backed projects and shows how differently they
wire Molecule today:

| Project | Community | License | Molecule layout today |
|---|---|---|---|
| linux-system-roles (network, storage) | linux-system-roles | BSD-3-Clause / MIT | No Molecule. Its own `tests/` playbooks, run by tox-lsr and Testing Farm |
| dev-sec/ansible-collection-hardening | dev-sec | Apache-2.0 | Top-level `molecule/`, a project-local `../shared/` |
| prometheus-community/ansible | prometheus-community | Apache-2.0 | Per-role `roles/*/molecule/`, a `_common` role |
| aristanetworks/avd | Arista | Apache-2.0 | `extensions/molecule/`, 30 scenarios, Makefile-managed |
| nginxinc/ansible-role-nginx | NGINX / F5 | Apache-2.0 | Top-level `molecule/`, a `common/` Dockerfile shim |
| openstack/ansible-role-systemd_service | OpenStack | Apache-2.0 | Single `molecule/default`, playbooks pulled from `tests/` |
| osism/ansible-collection-commons | OSISM | Apache-2.0 | Top-level `molecule/`, a large delegated `prepare/` tree |
| david-igou/ansible-collection-armbian | David Igou | MIT | `extensions/molecule/`, 10 scenarios, a shared `config.yml`, a per-scenario `inventory/` tree |
| david-igou/ansible-collection-routeros_configuration | David Igou | MIT | `extensions/molecule/`, 22 scenarios, `shared_state: true` in a shared `config.yml`, a `Makefile`-ordered run |

That is at least seven distinct layouts across these projects. The variation is the symptom.

## The proposal

One `molecule.yml` at the project root carries the run config, the scenario declarations,
and the parent and child edges. Shared playbooks live once under `playbooks/molecule/` and
are referenced by name. See `design/docs/the-pattern.md`.

Some `after/` examples reference relocated molecule stage playbooks by collection FQCN
(`<collection>.molecule_<scenario>_<stage>`). That form assumes molecule's FQCN stage
reference fix, open issue https://github.com/ansible/molecule/issues/4244, not yet merged.

## The result

Each project's per-scenario config collapses into one root `molecule.yml`. The count covers only
the files that describe or orchestrate the test suite, not the playbooks or fixture data, which are
unchanged and still referenced.

| Project | Config files | Scenario folders | Lines |
|---|---|---|---|
| aristanetworks/avd | 32 → 1 | 30 → 0 | 914 → 342 |
| david-igou/ansible-collection-armbian | 41 → 1 | 10 → 0 | 328 → 164 |
| david-igou/ansible-collection-routeros_configuration | 25 → 1 | 22 → 0 | 331 → 253 |
| nginxinc/ansible-role-nginx | 15 → 1 | 14 → 0 | 3042 → 866 |
| dev-sec/ansible-collection-hardening | 11 → 1 | 7 → 0 | 451 → 260 |
| prometheus-community/ansible | 11 → 1 | 9 → 0 | 249 → 274 |
| osism/ansible-collection-commons | 4 → 1 | 2 → 0 | 521 → 54 |
| openstack/ansible-role-systemd_service | 4 → 1 | 1 → 0 | 151 → 44 |
| linux-system-roles/network | 5 → 1 | 0 | 622 → 213 |
| linux-system-roles/storage | 8 → 1 | 0 | 1029 → 164 |
| Total, the Molecule projects | 143 → 8 | 95 → 0 | 5987 → 2257 |

prometheus-community/ansible is counted over a representative three-role subset, and it is the one
project here whose single file is not shorter than what it replaces, because its scenarios already
share one 96-line config. The two linux-system-roles projects use no Molecule today, so they are
measured differently: their test config is spread across several separate systems, and the
single-config layout gathers it into one file. They are shown but not summed into the totals.

## What is in here

For each project, `examples/<project>/` holds:

- `before/`: the real testing files, copied from a pinned upstream commit, licenses intact.
- `after/`: the same run expressed in the single top-level layout.
- `README.md`: the specific duplication that project carried, and what the refactor removes.

The rest of the repo says what may be edited by hand:

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
