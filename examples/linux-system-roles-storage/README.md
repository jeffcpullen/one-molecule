# linux-system-roles/storage, three forms

This is a proof of concept of a testing layout idea, in three folders. linux-system-roles/storage
(pinned at commit `bd96ce4e96f49906daf8dacd0ab9d286c60dc033` on `main`) uses no Molecule today. Its
tests are `tests/tests_*.yml` playbooks driven by tox-lsr, with `.fmf` plans and an `.ostree` path, run
against real VMs.

- `before/` copies a representative slice of that current layout verbatim.
- `in-between/` is a 1-to-1 conversion into the Molecule shape that ships today: scenarios under
  `extensions/molecule/`, shared machinery in `utils/`. It converts the two tests vendored in `before/`,
  both pass a full `molecule test` against a libvirt host (its README says what that needs), and it
  reproduces the `before/` disk provisioning faithfully.
- `after/molecule.yml` declares the same `tests/` playbooks in one root file. Molecule cannot run a
  single root config today, so the after shows how the layout would be authored, not a shipped setup.

The three read as a progression: their process now, the same tests in current Molecule, and the proposed
single-file form.

## Changed

| | Before | In-between | After |
|---|---|---|---|
| Test config locations (tox.ini, .fmf/, .ostree/, plans/, tests/.fmf/, tests/provision.fmf, tests/vars/, tests/tasks/) | 8 | extensions/molecule/ (config.yml + utils/ shared once, converge-only per scenario) | 1 |
| Test playbooks (tests/tests_*.yml) | 150 (50 distinct groups, the other 100 generated nvme and scsi variants) | 2 scenario dirs under extensions/molecule, the 2 tests vendored in before/ | 50 scenarios in one file |
| Runnable with today's Molecule | not Molecule | yes, both scenarios pass `molecule test` (molecule 25.9.0 or later, a libvirt host) | no |

The 150 playbooks and 50 groups are counted in the upstream `tests/` tree at the pinned commit, which is
also the 1.22.1 release. `before/` copies 2 of them, and `in-between/` converts only those 2.
