# linux-system-roles/storage, as-is Molecule form

The runnable middle of the three folders. `before/` is a slice of the role's current process (tox-lsr,
`.fmf` plans, `standard-inventory-qcow2`, real VMs). `after/` is the proposed single-file
`molecule.yml`, which Molecule cannot parse today. This `in-between/` is a **1-to-1 conversion into the
Molecule folder shape that ships today**: scenarios under `extensions/molecule/`, shared machinery in
`extensions/molecule/utils/`, matching the ansible-creator collection scaffold.

Everything a test needs except the role itself is vendored, so the conversion is self-contained. Each
scenario's `converge` is a single playbook (`utils/playbooks/<scenario>.yml`, the role's own
`tests_<scenario>.yml`). Everything those playbooks include, the verifiers, the `test-verify-*` chain,
and the `setup` / `run_role_with_clear_facts` / `get_unused_disk` task helpers, is the shared LSR test
library, vendored once under `utils/playbooks/shared/`. The only files edited are the two converge
playbooks, and only their include prefixes, repointed at `shared/`, plus a licence and change header.
Their test logic is untouched. The
one thing not vendored is the storage role itself (invoked as `linux-system-roles.storage`), so it is
not runnable from inside this example.

## The reuse this makes visible

A single `luks` converge run touches 32 files, and 31 of them are that shared library (the
`test-verify-*` / `verify-pool-*` chain alone is 24). They are the same `.github`-distributed files
every LSR role and every one of the 41 storage scenarios pulls in, which is why they live once in
`shared/` and each scenario adds only its converge on top. Convert a second role and it reuses the same
`shared/` tree rather than copying it. The scenario-specific surface is one playbook riding on a large
shared substrate.

## The lifecycle, read as objects not hosts

`create` makes the objects `converge` acts on, `destroy` removes them, `cleanup` unwinds side effects.
For storage the objects are the nine disks. `create.yml` boots a transient libvirt domain with those
disks, `converge` is the role's test playbook whose `shared/tasks/get_unused_disk.yml` discovers them,
`destroy` tears the domain down, and `cleanup` is a no-op because a fresh node is made per scenario.

The disk objects are a faithful translation of `before/tests/provision.fmf` through
`standard-inventory-qcow2` (tox-lsr): nine raw sparse files, `format=raw`, virtio by `if=virtio`, scsi
via a `virtio-scsi` controller, nvme via a `-device nvme` passthrough. `utils/vars/disks.yml` carries
the sizes byte-for-byte.

## Folder shape

```
in-between/
  galaxy.yml                            collection root, without which config.yml is never loaded
  extensions/
    molecule/
      config.yml                        auto-loaded base config: driver, env, vars, create/destroy/cleanup
      utils/
        playbooks/
          create.yml                    make the domain + nine disks
          destroy.yml                   remove them
          cleanup.yml                   no-op (ephemeral node)
          default.yml                   default scenario converge (role's tests_default.yml)
          luks.yml                      luks scenario converge (role's tests_luks.yml)
          shared/                       the LSR test library, vendored once
            verify-role-results.yml  verify-role-failed.yml  verify-data-preservation.yml
            create-test-file.yml
            test-verify-*.yml  verify-pool-*.yml     (the verify chain, 24 files)
            tasks/
              setup.yml  run_role_with_clear_facts.yml  get_unused_disk.yml
          templates/
            domain.xml.j2               interface -> bus, nvme via qemu:commandline
            user-data.j2                cloud-init NoCloud
        vars/
          disks.yml                     the nine drives, from provision.fmf
      default/molecule.yml              converge: ../utils/playbooks/default.yml
      luks/molecule.yml                 converge: ../utils/playbooks/luks.yml
      <39 more>/molecule.yml            one per scenario, converge only
```

The scaffold reference is ansible-creator's collection template: scenarios at
`extensions/molecule/<scenario>/molecule.yml`, shared playbooks at
`extensions/molecule/utils/playbooks/`, shared vars at `extensions/molecule/utils/vars/`.

Molecule auto-loads a base config from `extensions/molecule/config.yml` and deep-merges each scenario's
`molecule.yml` on top, with no `--base-config` flag. It does that only inside a collection, which is why
this tree carries a `galaxy.yml`: with no collection root the search finds nothing, and because a
missing playbook is a warning rather than an error, `molecule create` then exits 0 having created
nothing. So the
shared blocks (driver, env, vars, create/destroy/cleanup) live in `config.yml` once and every scenario
file is just its `converge`. The single knob that varies across 41 scenarios is the converge playbook,
which is what the `after/` single-file form turns into one list.

## Changed

| | Before | In-between |
|---|---|---|
| Disk provisioning | provision.fmf via standard-inventory-qcow2 | utils/playbooks/create.yml + domain.xml.j2 (same disks) |
| Shared config | .github-managed vars, harness env | extensions/molecule/config.yml (auto-loaded once) |
| Molecule lifecycle | tox-lsr, .fmf plans | utils/playbooks/ (create/destroy/cleanup once) |
| Test library | injected per role from .github | utils/playbooks/shared/ (vendored once, 31 files) |
| Per-scenario file | tox-lsr conventions, .fmf plans | one converge playbook, everything else shared |
| Scenarios | 41 distinct test groups | 41 dirs under extensions/molecule, 2 shown |

## Caveats

Unrun (no libvirt host here). Needs `community.libvirt`, `community.crypto`, `cloud-localds`, and a base
cloud image (`MOLECULE_BASE_IMAGE`, default a Fedora cloud qcow2). nvme is the one literal qemu
passthrough, since libvirt has no native nvme bus. The `shared/` library is byte-for-byte upstream
(storage at `bd96ce4e96f49906daf8dacd0ab9d286c60dc033`). Only the two converge playbooks were edited,
and only their include prefixes and a licence and change header. The two scenarios shown are the ones whose test playbooks are vendored
in `before/`; the other 39 follow the same shape.
