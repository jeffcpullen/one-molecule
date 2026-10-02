# linux-system-roles/storage, as-is Molecule form

The runnable middle of the three folders. `before/` is a slice of the role's current process (tox-lsr,
`.fmf` plans, `standard-inventory-qcow2`, real VMs). `after/` is the proposed single-file
`molecule.yml`, which Molecule cannot parse today. This `in-between/` is a **1-to-1 conversion into the
Molecule folder shape that ships today**: scenarios under `extensions/molecule/`, shared machinery in
`extensions/molecule/utils/`, matching the ansible-creator collection scaffold.

Everything a test needs from the role's own test tree is vendored, so the conversion is
self-contained. Each scenario's `converge` is a single playbook (`utils/playbooks/<scenario>.yml`, the
role's own `tests_<scenario>.yml`). Everything those playbooks include, the verifiers, the
`test-verify-*` chain, the `setup` / `run_role_with_clear_facts` / `get_unused_disk` task helpers and
the two helper scripts, is the shared LSR test library, vendored once under `utils/playbooks/shared/`.
The four test modules and their `module_utils` sit beside it in `utils/playbooks/library/` and
`utils/playbooks/module_utils/`. The only files edited are the two converge playbooks, and only their
include prefixes, repointed at `shared/`, plus a licence and change header. Their test logic is
untouched. The storage role itself is not vendored. Molecule's dependency step installs it from
`extensions/molecule/requirements.yml` under the legacy name the tests call,
`linux-system-roles.storage`, pinned to 1.22.1, the release the vendored files come from.

## The reuse this makes visible

A `luks` converge reaches 40 files through its includes, module calls and module imports, counted
statically with conditional branches included. 39 of them are the vendored test machinery: the 33-file
`shared/` library (the `test-verify-*` / `verify-pool-*` chain alone is 24) and the 6 module files.
They are the same `.github`-distributed files every LSR role and every one of the 50 storage test groups
pulls in, which is why they live once in `shared/` and each scenario adds only its converge on top.
Convert a second role and it reuses the same `shared/` tree rather than copying it. The
scenario-specific surface is one playbook riding on a large shared substrate.

## The lifecycle, read as objects not hosts

`create` makes the objects `converge` acts on, `destroy` removes them, `cleanup` unwinds side effects.
For storage the objects are the nine disks. `create.yml` defines and boots a libvirt domain with those
disks, `converge` is the role's test playbook whose `shared/tasks/get_unused_disk.yml` discovers them,
`verify` checks the nine data disks are present on the node, `destroy` undefines the domain and removes
its files, and `cleanup` is a no-op because a fresh node is made per scenario.

The disk objects are a faithful translation of `before/tests/provision.fmf` through
`standard-inventory-qcow2` (tox-lsr): nine raw sparse files, `format=raw`, virtio on the virtio bus,
scsi via a `virtio-scsi` controller, and nvme on libvirt's native nvme bus with one controller per disk
carrying the same `def<n>` serial `standard-inventory-qcow2` gives its `-device nvme`.
`utils/vars/disks.yml` carries the sizes byte-for-byte and names no hypervisor. Each disk's
`guest_class` (virtio, scsi or nvme) is how the guest sees it, which fixes the device name prefix
`verify.yml` matches. `provision.fmf` leaves the class off its first three disks, and `disks.yml`
states virtio for them. `templates/domain.xml.j2` is the only place a class becomes a libvirt bus, so a
port to another hypervisor replaces that template and keeps `disks.yml`.

## Folder shape

```
in-between/
  galaxy.yml                            collection root, without which config.yml is never loaded
  extensions/
    molecule/
      config.yml                        auto-loaded base config: dependency, driver, env, vars, playbooks
      requirements.yml                  collections and the pinned role, for the dependency step
      utils/
        playbooks/
          create.yml                    make the domain + nine disks
          verify.yml                    check the nine data disks on the node
          destroy.yml                   remove them
          cleanup.yml                   no-op (ephemeral node)
          default.yml                   default scenario converge (role's tests_default.yml)
          luks.yml                      luks scenario converge (role's tests_luks.yml)
          shared/                       the LSR test library, vendored once (33 files)
            verify-role-results.yml  verify-role-failed.yml  verify-data-preservation.yml
            create-test-file.yml
            test-verify-*.yml  verify-pool-*.yml     (the verify chain, 24 files)
            tasks/
              setup.yml  run_role_with_clear_facts.yml  get_unused_disk.yml
            scripts/
              does_library_support.py  stratis_pool_info.py
          library/                      find_unused_disk, blockdev_info, resolve_blockdev, bsize
          module_utils/storage_lsr/     __init__.py, size.py
          templates/
            domain.xml.j2               guest_class -> libvirt bus, the only hypervisor mapping
            user-data.j2                cloud-init NoCloud
        vars/
          disks.yml                     the nine disks and their guest classes, from provision.fmf
          hypervisor.yml                libvirt URI, network, domain and work dir names
      default/molecule.yml              converge: ../utils/playbooks/default.yml
      luks/molecule.yml                 converge: ../utils/playbooks/luks.yml
```

The scaffold reference is ansible-creator's collection template: scenarios at
`extensions/molecule/<scenario>/molecule.yml`, shared playbooks at
`extensions/molecule/utils/playbooks/`, shared vars at `extensions/molecule/utils/vars/`.

Molecule auto-loads a base config from `extensions/molecule/config.yml` and deep-merges each scenario's
`molecule.yml` on top, with no `--base-config` flag. It does that only inside a collection, which is why
this tree carries a `galaxy.yml`. With no collection root the search finds nothing, and because a
missing playbook is a warning rather than an error, `molecule create` then exits 0 having created
nothing. So the shared blocks (dependency, driver, env, vars, create/destroy/cleanup/verify) live in
`config.yml` once and every scenario file is just its `converge`. The single knob that varies across the
50 test groups is the converge playbook, which is what the `after/` single-file form turns into one list.

## Running it

Run Molecule from this directory, for example `molecule test -s luks`. The collection is detected from a
`galaxy.yml` in the current working directory only, so run from anywhere else and the base config is
never loaded. The auto-load needs molecule 25.9.0 or later. A `.config/molecule/config.yml` at the root
of the enclosing git checkout takes precedence over it, and this repository has none.

The scenarios need a libvirt host with an active network named `default`, and a controller with the
libvirt client (`virsh`) and its Python bindings, `lxml`, `qemu-img` and `cloud-localds`. The
collections and the role are installed by the dependency step. Point `MOLECULE_BASE_IMAGE` at a cloud
qcow2 image whose cloud user is `cloud-user` (the default path is a Fedora cloud base image).
`LIBVIRT_DEFAULT_URI` defaults to `qemu:///system`. The ephemeral directory holds the disks, so it must
be traversable by the user the hypervisor runs qemu as. Relocate it with `MOLECULE_EPHEMERAL_DIRECTORY`
if it is not.

## Changed

| | Before | In-between |
|---|---|---|
| Disk provisioning | provision.fmf via standard-inventory-qcow2 | utils/playbooks/create.yml + domain.xml.j2 (same disks) |
| Shared config | .github-managed vars, harness env | extensions/molecule/config.yml (auto-loaded once) |
| Molecule lifecycle | tox-lsr, .fmf plans | utils/playbooks/ (create/verify/destroy/cleanup once) |
| Test library | injected per role from .github | utils/playbooks/shared/ (vendored once, 33 files) plus 6 module files |
| Per-scenario file | tox-lsr conventions, .fmf plans | one converge playbook, everything else shared |
| Scenarios | 50 distinct test groups (150 playbooks) | 2 scenario dirs under extensions/molecule, one per vendored test |

## Caveats

Only 2 of the 50 test groups are converted, the two whose test playbooks are vendored in `before/`.
The other 48 follow the same shape and are not here. Both converted scenarios pass a full
`molecule test` against a libvirt host. The default test sequence runs without `idempotence` and
`side_effect`, because the LSR test playbooks create and remove volumes and provoke role failures on
purpose. The vendored files are byte-for-byte upstream (storage at
`bd96ce4e96f49906daf8dacd0ab9d286c60dc033`, tag 1.22.1). Only the two converge playbooks were edited,
and only their include prefixes and a licence and change header.
