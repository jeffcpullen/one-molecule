# linux-system-roles/storage, three forms

This is a proof of concept of a testing layout idea, in three folders. linux-system-roles/storage
(pinned at commit `75bb17d104c8e2327827d81ff5e653b84082fb57` on `main`) uses no Molecule today. Its
tests are `tests/tests_*.yml` playbooks driven by tox-lsr, with `.fmf` plans and an `.ostree` path, run
against real VMs.

- `before/` copies a representative slice of that current layout verbatim.
- `in-between/` is a 1-to-1 conversion into the Molecule shape that ships today: scenarios under
  `extensions/molecule/`, shared machinery in `utils/`, and the role itself under `roles/storage/`. It
  converts the two tests vendored in `before/`. Both passed a full `molecule test` against a libvirt
  host at release 1.22.1 and have not been rerun at this commit (its README says what a run needs). It
  provisions one ordered list of the three scsi disks from `before/` and gives each scenario the first
  N it needs, labelling every disk so the tests select disks by label rather than by upstream's kernel
  driver match. It drops the virtio and nvme disks and the nvme coverage, and its README states each
  divergence and records the disk count every test group needs.
- `after/molecule.yml` declares the same `tests/` playbooks in one root file, with the in-between's
  disk count as a default of 1 that the 19 scenarios needing 0, 2 or 3 disks override. Molecule cannot
  run a single root config today, so the after shows how the layout would be authored, not a shipped
  setup.

The three read as a progression: their process now, the same tests in current Molecule, and the proposed
single-file form.

## Changed

| | Before | In-between | After |
|---|---|---|---|
| Test config locations (tox.ini, .fmf/, .ostree/, plans/, tests/.fmf/, tests/provision.fmf, tests/vars/, tests/tasks/) | 8 | extensions/molecule/ (config.yml + utils/ shared once, converge-only per scenario) | 1 |
| Test playbooks (tests/tests_*.yml) | 151 (51 distinct groups, the other 100 generated nvme and scsi variants) | 2 scenario dirs under extensions/molecule, the 2 tests vendored in before/ | 51 scenarios in one file, 19 with a disk count override |
| Runnable with today's Molecule | not Molecule | yes, both scenarios passed `molecule test` at release 1.22.1, not rerun at this commit (molecule 25.9.0 or later, a libvirt host) | no |

The 151 playbooks and 51 groups are counted in the upstream `tests/` tree at the pinned commit, which is
unreleased. The latest release, 1.22.1, has 150 and 50, and `tests_invalid_input.yml` is the group added
since. `before/` copies 2 of them, and `in-between/` converts only those 2.
